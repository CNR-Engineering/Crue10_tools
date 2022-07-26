# coding: utf-8
from builtins import super  # Python2 fix
from collections import OrderedDict
from copy import deepcopy
import numpy as np
import os.path
import shutil
import time

from crue10.base import EnsembleFichiersXML
from crue10.modele import Modele
from crue10.run import get_run_identifier, Run
from crue10.utils import check_isinstance, check_preffix, duration_iso8601_to_seconds, duration_seconds_to_iso8601, \
    ExceptionCrue10, extract_pdt_from_elt, get_optional_commentaire, \
    logger, parse_loi, PREFIX, write_default_xml_file, write_xml_from_tree
from crue10.utils.settings import CRUE10_EXE_PATH
from crue10.utils.sorties import Sorties
from .calcul import Calcul, CalcPseudoPerm, CalcTrans
from .loi_hydraulique import LoiHydraulique


class OrdCalcPseudoPerm:
    """
    OrdCalcPseudoPerm = paramètres des calculs permanents

    :ivar id: nom du calcul
    :vartype id: str
    :ivar init: méthode d'initialisation (IniCalcCI|IniCalcPrecedent|IniCalcCliche) et chemin du cliché
    :vartype init: (str, str)
    :ivar cliche_fin: chemin du cliché
    :vartype cliche_fin: str
    """
    def __init__(self, calc_id, calc_init, cliche_fin):
        self.id = calc_id
        self.init = calc_init
        self.cliche_fin = cliche_fin


class OrdCalcTrans:
    """
    OrdCalcTrans = paramètres des calculs transitoires

    :ivar id: nom du calcul
    :vartype id: str
    :ivar duree: durée du calcul
    :vartype duree: float
    :ivar pdt_res: pas de temps de sortie des résultats
    :vartype pdt_res: float|list
    :ivar init: méthode d'initialisation (IniCalcCI|IniCalcPrecedent|IniCalcCliche) et chemin du cliché
    :vartype init: (str, str)
    :ivar cliche_ponctuel: chemin et temps d'extraction du cliché ponctuel
    :vartype cliche_ponctuel: (str, str)
    :ivar cliche_periodique: chemin et pas de temps du cliché périodique
    :vartype cliche_periodique: (str, str)
    """

    def __init__(self, calc_id, duree, pdt_res, calc_init, cliche_ponctuel, cliche_periodique):
        """
        :param calc_id: nom du calcul
        :type calc_id: str
        :param duree: durée en secondes
        :type duree: float
        :param pdt_res: pas de temps (constant ou variable)
        :type pdt_res: float|list
        :param calc_init: initialisation du calcul
        :type calc_init: tuple
        :param cliche_ponctuel: cliché ponctuel
        :param cliche_periodique: cliché périodique
        """
        check_isinstance(duree, float)
        check_isinstance(pdt_res, (float, list))
        self.id = calc_id
        self.duree = duree
        self.pdt_res = pdt_res
        self.init = calc_init
        self.cliche_ponctuel = cliche_ponctuel
        self.cliche_periodique = cliche_periodique

    def get_duree_in_iso8601(self):
        """Obtenir la durée en ISO8601"""
        return duration_seconds_to_iso8601(self.duree)

    def is_pdt_res_cst(self):
        """Dispose d'un pas de temps constant"""
        return isinstance(self.pdt_res, float)

    def get_pdt_res_in_iso8601(self):
        """Obtenir le pas de temps (constant ou variable) en ISO8601"""
        if self.is_pdt_res_cst():
            return duration_seconds_to_iso8601(self.pdt_res)
        else:
            res = []
            for (nb_pdt, pdt_float) in self.pdt_res:
                res.append((nb_pdt, duration_seconds_to_iso8601(pdt_float)))
            return res


class Scenario(EnsembleFichiersXML):
    """
    Scénario Crue10

    :ivar id: nom du scénario
    :vartype id: str
    :ivar modele: modèle
    :vartype modele: Modele
    :ivar calculs: liste des calculs
    :vartype calculs: list(Calcul)
    :ivar liste_ord_calc_pseudoperm: liste des paramètres des calculs permanents
    :vartype liste_ord_calc_pseudoperm: list(OrdCalcPseudoPerm)
    :ivar liste_ord_calc_trans: liste des paramètres des calculs transitoires
    :vartype liste_ord_calc_trans: list(OrdCalcTrans)
    :ivar lois_hydrauliques: dictionnaire des lois hydrauliques
    :vartype lois_hydrauliques: OrderedDict(LoiHydraulique)
    :ivar runs: dictionnaire des runs
    :vartype runs: OrderedDict(Run)
    :ivar current_run_id: nom du scénario courant
    :vartype current_run_id: str
    """

    FILES_XML = ['ocal', 'ores', 'pcal', 'dclm', 'dlhy']
    FILES_XML_WITHOUT_TEMPLATE = ['ores', 'pcal']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, nom_scenario, modele, mode='r', files=None, metadata=None, version_grammaire=None):
        """
        :param nom_scenario: nom du scénario
        :type nom_scenario: str
        :param modele: modèle
        :type modele: Modele
        :param mode: accès en lecture ('r') ou écriture ('w')
        :type mode: str
        :param files: dictionnaire des chemins vers les fichiers xml
        :type files: dict(str)
        :param metadata: dictionnaire avec les méta-données
        :type metadata: dict(str)
        :param version_grammaire: version de la grammaire
        :type version_grammaire: str
        """
        check_preffix(nom_scenario, 'Sc_')
        self.id = nom_scenario
        super().__init__(mode, files, metadata, version_grammaire=version_grammaire)

        self.calculs = []
        self.liste_ord_calc_pseudoperm = []  # OrdCalcPseudoPerm
        self.liste_ord_calc_trans = []  # OrdCalcTrans
        self.lois_hydrauliques = OrderedDict()

        self.modele = None
        self.set_modele(modele)

        self.ocal_sorties = Sorties()

        self.current_run_id = None
        self.runs = OrderedDict()

    def get_function_apply_modifications(self, etude):
        """
        Obtenir la fonction qui permet d'appliquer les modifications et de lancer un Run associé

        :param etude: étude
        :type etude: Etude
        :return: function
        """
        curr_etude = deepcopy(etude)
        curr_etude.ignore_others_scenarios(self.id)

        def fun(modifications):
            """
            Applique les modifications demandées sur une copie du scénario courant et lance un Run complet
            @return: Run
            """
            # self is not shared across thread but is successively modified (per thread),
            # therefore a deep copy is performed:
            curr_scenario = deepcopy(self)
            run_id = modifications.pop('run_id')
            try:
                comment = modifications.pop('comment')
            except KeyError:
                comment = ''
            curr_scenario.apply_modifications(modifications)
            return curr_scenario.create_and_launch_new_run(curr_etude, run_id=run_id, comment=comment, force=True)

        return fun

    def ajouter_calcul(self, calcul):
        """
        Ajouter un calcul au scénario

        :param calcul: calcul (pseudo-permanent ou transitoire) à ajouter
        :type calcul: CalcPseudoPerm | CalcTrans
        """
        check_isinstance(calcul, Calcul)
        self.calculs.append(calcul)

    def ajouter_loi_hydraulique(self, loi_hydraulique):
        """
        Ajouter une loi hydraulique au scénario

        :param run: loi hydraulique à ajouter
        :type run: LoiHydraulique
        """
        check_isinstance(loi_hydraulique, LoiHydraulique)
        self.lois_hydrauliques[loi_hydraulique.id] = loi_hydraulique

    def ajouter_run(self, run):
        """
        Ajouter un Run au scénario

        :param run: run à ajouter
        :type run: Run
        """
        check_isinstance(run, Run)
        if run.id in self.runs:
            raise ExceptionCrue10("Le Run %s est déjà présent" % run.id)
        self.runs[run.id] = run

    def get_calcul(self, nom_calcul):
        """
        :param nom_calcul: nom du calcul demandé
        :rtype: Calcul
        """
        for calcul in self.calculs:
            if calcul.id == nom_calcul:
                return calcul
        raise ExceptionCrue10("Le calcul `%s` n'existe pas" % nom_calcul)

    def get_ord_calc_pseudoperm(self, nom_calcul):
        """
        :param nom_calcul: nom du calcul pseudo-permanent demandé
        :rtype: OrdCalcPseudoPerm
        """
        for ord_calc in self.liste_ord_calc_pseudoperm:
            if nom_calcul == ord_calc.id:
                return ord_calc
        self.get_calcul(nom_calcul)  # Check that the calculation exists
        raise ExceptionCrue10("Le calcul pseudo-permanent `%s` n'est pas actif" % nom_calcul)

    def get_ord_calc_trans(self, nom_calcul):
        """
        :param nom_calcul: nom du calcul transitoire demandé
        :rtype: OrdCalcTrans
        """
        for ord_calc in self.liste_ord_calc_trans:
            if nom_calcul == ord_calc.id:
                return ord_calc
        self.get_calcul(nom_calcul)  # Check that the calculation exists
        raise ExceptionCrue10("Le calcul transitoire `%s` n'est pas actif" % nom_calcul)

    def get_nb_calc_pseudoperm_actif(self):
        """
        :return: nombre de calculs pseudo-permanents actifs
        :rtype: int
        """
        return len(self.liste_ord_calc_pseudoperm)

    def get_nb_calc_trans_actif(self):
        """
        :return: nombre de calculs transitoires actifs
        :rtype: int
        """
        return len(self.liste_ord_calc_trans)

    def get_liste_calc_pseudoperm(self, ignore_inactive=False):
        """
        Obtenir la liste des calculs pseudo-permanents

        :param ignore_inactive: True pour ignorer les calculs inactifs
        :rtype: list(CalcPseudoPerm)
        """
        calculs = []
        for calcul in self.calculs:
            if isinstance(calcul, CalcPseudoPerm):
                if ignore_inactive:
                    if calcul.id in [ord.id for ord in self.liste_ord_calc_pseudoperm]:
                        calculs.append(calcul)
                else:
                    calculs.append(calcul)
        return calculs

    def get_liste_calc_trans(self, ignore_inactive=False):
        """
        Obtenir la liste des calculs transitoires

        :param ignore_inactive: True pour ignorer les calculs inactifs
        :rtype: list(CalcTrans)
        """
        calculs = []
        for calcul in self.calculs:
            if isinstance(calcul, CalcTrans):
                if ignore_inactive:
                    if calcul.id in [ord.id for ord in self.liste_ord_calc_trans]:
                        calculs.append(calcul)
                else:
                    calculs.append(calcul)
        return calculs

    def get_run(self, run_id):
        """
        Obtenir un run à patir de son nom

        :param run_id: nom du run
        :rtype: Run
        """
        if not self.runs:
            raise ExceptionCrue10("Aucun run n'existe pour ce scénario")
        run = None
        try:
            run = self.runs[run_id]
        except KeyError:
            raise ExceptionCrue10("Le run %s n'existe pas !\nLes noms possibles sont: %s"
                                  % (run_id, list(self.runs.keys())))
        run.read_traces()
        return run

    def get_last_run(self):
        """
        Obtenir le dernier run

        :return: dernier run
        :rtype: Run
        """
        if not self.runs:
            raise ExceptionCrue10("Aucun run n'existe pour ce scénario")
        run_id = list(self.runs.keys())[-1]
        return self.get_run(run_id)

    def get_liste_run_ids(self):
        """
        Obtenir la liste des noms de runs

        :return: liste des noms des runs
        :rtype: list(str)
        """
        return [run_id for run_id, _ in self.runs.items()]

    def get_loi_hydraulique(self, nom_loi):
        """
        Obtenir la loi hydraulique à partir de son nom

        :param nom_loi: nom de la loi hydraulique
        :rtype: LoiHydraulique
        """
        try:
            return self.lois_hydrauliques[nom_loi]
        except KeyError:
            raise ExceptionCrue10("La loi `%s` n'existe pas" % nom_loi)

    def set_modele(self, modele):
        """
        Affecter le modèle au scénario

        :param modele: modèle à affecter
        :type modele: Modele
        """
        check_isinstance(modele, Modele)
        self.modele = modele

    def set_current_run_id(self, run_id):
        if run_id not in self.runs:
            raise ExceptionCrue10("Le Run '%s' n'existe pas" % run_id)
        self.current_run_id = run_id

    def set_ocal_OrdCalcTrans_DureeCalc(self, calc_name, value):
        """
        Affecter la durée fournie pour le calcul transitoire demandé

        :param calc_name: nom du calcul transitoire
        :type calc_name: str
        :param value: durée (en secondes)
        :type value: float
        """
        check_isinstance(value, float)
        elt = self._get_ocal_OrdCalcTrans(calc_name).find(PREFIX + 'DureeCalc')
        elt.text = duration_seconds_to_iso8601(value)

    def set_ocal_OrdCalcTrans_PdtCst(self, calc_name, value):
        """
        Affecter le pas de temps de sortie fourni pour le calcul transitoire demandé

        :param calc_name: nom du calcul transitoire
        :type calc_name: str
        :param value: pas de temps (en secondes)
        :type value: float
        """
        check_isinstance(value, float)
        elt = self._get_ocal_OrdCalcTrans(calc_name).find(PREFIX + 'PdtRes').find(PREFIX + 'PdtCst')
        elt.text = duration_seconds_to_iso8601(value)

    def apply_modifications(self, modifications):
        """
        Modifie le scénario courant à partir d'un dictionnaire décrivant les modifications

        Les modifications possibles sont :

        ## Sur le scénario ou modèle

        - `pnum.CalcPseudoPerm.Pdt`: <float> => affection du pas de temps (en secondes) pour les calculs permanents
        - `pnum.CalcPseudoPerm.TolMaxZ`: <float> => affection de la tolérance en niveau (en m) pour les calculs
          permanents
        - `pnum.CalcPseudoPerm.TolMaxQ`: <float> => affection de la tolérance en débit (en m3/s) pour les calculs
          permanents
        - `Qapp_factor.NomCalcul.NomNoeud`: <float> => application du facteur multiplicatif au débit du calcul
          NomCalcul au noeud nommé NomNoeud
        - `Zimp.NomCalcul.NomNoeud`: <float> => application de la cote au calcul NomCalcul au noeud nommé NomNoeud
        - `branche_barrage.CoefD`: <float> => application du coefficient à la branche barrage

        ## Sur les sous-modèles

        - `Fk_NomLoi`: <float> => modification du Strickler de la loi de frottement nommée NomLoi
        - `Fk_shift.*`: <float> => modification par somme du Strickler de toutes les lois de frottement (sauf celles du stockage)

        :param modifications: dictionnaire des modifications
        :type modifications: dict
        """
        check_isinstance(modifications, dict)
        for modification_key, modification_value in modifications.items():
            # Numerical parameters
            if modification_key == 'pnum.CalcPseudoPerm.Pdt':
                self.modele.set_pnum_CalcPseudoPerm_PdtCst(modification_value)
            elif modification_key == 'pnum.CalcPseudoPerm.TolMaxZ':
                self.modele.set_pnum_CalcPseudoPerm_TolMaxZ(modification_value)
            elif modification_key == 'pnum.CalcPseudoPerm.TolMaxQ':
                self.modele.set_pnum_CalcPseudoPerm_TolMaxQ(modification_value)

            # Hydraulic parameters
            elif modification_key == 'branche_barrage.CoefD':
                branche_barrage = self.modele.get_branche_barrage()
                branche_barrage.liste_elements_seuil[:, 2] = modification_value
            elif modification_key == 'Fk_shift.*':
                for loi in self.modele.get_liste_lois_frottement(ignore_sto=True):
                    loi.shift_loi_Fk_values(modification_value)
            elif modification_key.startswith('Fk_'):
                loi = self.modele.get_loi_frottement(modification_key)
                loi.set_loi_constant_value(modification_value)
            elif modification_key.startswith('Qapp_factor.'):
                _, nom_calcul, nom_noeud = modification_key.split('.', 2)
                calcul = self.get_calcul(nom_calcul)
                calcul.multiplier_valeur(nom_noeud, modification_value)
            elif modification_key.startswith('Zimp.'):
                _, nom_calcul, nom_noeud = modification_key.split('.', 2)
                calcul = self.get_calcul(nom_calcul)
                calcul.set_valeur(nom_noeud, modification_value)
            else:
                raise ExceptionCrue10("La modification `%s` n'est pas reconnue. "
                                      "Voyez la documentation de Scenario.apply_modifications" % modification_key)

    def _read_dclm(self):
        """
        Lire le fichier dclm.xml
        """
        root = self._get_xml_root_set_version_grammaire_and_comment('dclm')

        for elt_calc in root:
            if elt_calc.tag == PREFIX + 'CalcPseudoPerm':
                calc_perm = CalcPseudoPerm(elt_calc.get('Nom'), get_optional_commentaire(elt_calc))
                for elt_valeur in elt_calc:
                    if elt_valeur.tag == (PREFIX + 'Commentaire'):
                        continue

                    clim_type = elt_valeur.tag[len(PREFIX):]
                    if clim_type not in CalcPseudoPerm.CLIM_TYPE_TO_TAG_VALUE:
                        raise ExceptionCrue10("Type de Clim inconnu: %s" % clim_type)

                    if clim_type == 'CalcPseudoPermBrancheOrificeManoeuvre':
                        sens = elt_valeur.find(PREFIX + 'SensOuv').text
                    else:
                        sens = None

                    value_elt = elt_valeur.find(PREFIX + CalcPseudoPerm.CLIM_TYPE_TO_TAG_VALUE[clim_type])
                    value = float(value_elt.text)
                    typ_loi = CalcPseudoPerm.CLIM_TYPE_TO_TAG_VALUE[clim_type]

                    calc_perm.ajouter_valeur(
                        elt_valeur.get('NomRef'),
                        clim_type,
                        elt_valeur.find(PREFIX + 'IsActive').text == 'true',
                        value,
                        sens,
                        typ_loi,
                    )

                self.ajouter_calcul(calc_perm)

            if elt_calc.tag == PREFIX + 'CalcTrans':
                calc_trans = CalcTrans(elt_calc.get('Nom'), get_optional_commentaire(elt_calc))
                for elt_valeur in elt_calc:
                    if elt_valeur.tag == (PREFIX + 'Commentaire'):
                        continue

                    clim_type = elt_valeur.tag[len(PREFIX):]
                    if clim_type not in CalcTrans.CLIM_TYPE_TO_TAG_VALUE and \
                            clim_type not in CalcTrans.CLIM_TYPE_SPECIAL_VALUE:
                        raise ExceptionCrue10("Type de Clim inconnu: %s" % clim_type)

                    if clim_type == 'CalcTransBrancheOrificeManoeuvre' or clim_type == 'CalcTransBrancheOrificeManoeuvreRegul':
                        sens = elt_valeur.find(PREFIX + 'SensOuv').text
                    else:
                        sens = None

                    value_elt = None
                    nom_loi = None
                    typ_loi = None
                    nom_fic = None
                    param_loi = None
                    if clim_type in CalcTrans.CLIM_TYPE_TO_TAG_VALUE:
                        typ_loi = CalcTrans.CLIM_TYPE_TO_TAG_VALUE[clim_type]
                        value_elt = elt_valeur.find(PREFIX + typ_loi)
                        if value_elt is not None:
                            nom_loi = value_elt.get('NomRef')  # TODO: check law exists
                    if value_elt is None and clim_type in CalcTrans.CLIM_TYPE_SPECIAL_VALUE:
                        typ_loi = CalcTrans.CLIM_TYPE_SPECIAL_VALUE[clim_type]
                        value_elt = elt_valeur.find(PREFIX + typ_loi)
                        if value_elt is not None:
                            # CLimM externe ou CLimM manoeuvre
                            nom_loi = value_elt.get('NomRef')
                            param_loi = value_elt.get('Param')
                            nom_fic = value_elt.get('NomFic')
                    calc_trans.ajouter_valeur(
                        elt_valeur.get('NomRef'),
                        clim_type,
                        elt_valeur.find(PREFIX + 'IsActive').text == 'true',
                        nom_loi,
                        sens,
                        typ_loi,
                        param_loi,
                        nom_fic
                    )

                self.ajouter_calcul(calc_trans)

    def _read_dlhy(self):
        """
        Lire le fichier dlhy.xml
        """
        root = self._get_xml_root_set_version_grammaire_and_comment('dlhy')

        for elt_loi in root.find(PREFIX + 'Lois'):  # LoiDF, LoiFF
            loi_hydraulique = LoiHydraulique(elt_loi.get('Nom'), elt_loi.get('Type'),
                                             comment=get_optional_commentaire(elt_loi))
            if loi_hydraulique.est_temporel():
                date_zero = elt_loi.find(PREFIX + 'DateZeroLoiDF').text
                if date_zero is not None:
                    loi_hydraulique.set_date_zero(date_zero)
            loi_hydraulique.set_values(parse_loi(elt_loi))
            self.ajouter_loi_hydraulique(loi_hydraulique)

    def _read_ocal(self):
        """
        Lire le fichier ocal.xml
        """
        root = self._get_xml_root_set_version_grammaire_and_comment('ocal')

        # Read Sorties
        elt = root.find(PREFIX + 'Sorties')
        self.ocal_sorties.set_avancement(elt.find(PREFIX + 'Avancement'))
        self.ocal_sorties.set_trace(elt.find(PREFIX + 'Trace'))
        self.ocal_sorties.set_resultat(elt.find(PREFIX + 'Resultat'))

        # Read active calculations options
        for elt in root.findall(PREFIX + 'OrdCalcPseudoPerm'):
            # NomRef ; IniCalcCI|IniCalcPrecedent|IniCalcCliche, PrendreClicheFinPermanent

            elt_init = elt[0]

            elt_cliche_fin = elt.find(PREFIX + 'PrendreClicheFinPermanent')
            if elt_cliche_fin is None:
                cliche_fin = None
            else:
                cliche_fin = elt_cliche_fin.get('NomFic')

            ord_calc = OrdCalcPseudoPerm(elt.get('NomRef'), (elt_init.tag[len(PREFIX):], elt_init.get('NomFic')),
                                         cliche_fin)
            self.liste_ord_calc_pseudoperm.append(ord_calc)

        for elt in root.findall(PREFIX + 'OrdCalcTrans'):
            # NomRef ; DureeCalc, PdtRes, IniCalcCI|IniCalcPrecedent|IniCalcCliche,
            #          PrendreClichePonctuel, PrendreClichePeriodique

            elt_init = elt[2]

            elt_cliche_ponctuel = elt.find(PREFIX + 'PrendreClichePonctuel')  # TODO: should support multiple? Or change XSD to add `maxOccurs="1"`
            if elt_cliche_ponctuel is None:
                cliche_ponctuel = None
            else:
                cliche_ponctuel = (elt_cliche_ponctuel.get('NomFic'), elt_cliche_ponctuel[0].text)

            elt_cliche_periodique = elt.find(PREFIX + 'PrendreClichePeriodique')  # TODO: should support multiple? Or change XSD to add `maxOccurs="1"`
            if elt_cliche_periodique is None:
                cliche_periodique = None
            else:
                assert elt_cliche_periodique[0][0].tag.endswith('PdtCst')  # TODO: should support PdtVar?
                cliche_periodique = (elt_cliche_periodique.get('NomFic'), elt_cliche_periodique[0][0].text)

            ord_calc = OrdCalcTrans(elt.get('NomRef'),
                                    duration_iso8601_to_seconds(elt[0].text),
                                    extract_pdt_from_elt(elt[1]),
                                    (elt_init.tag[len(PREFIX):], elt_init.get('NomFic')),
                                    cliche_ponctuel, cliche_periodique)
            self.liste_ord_calc_trans.append(ord_calc)

    def read_all(self):
        """Lire tous les fichiers du scénario"""
        if not self.was_read:
            self._set_xml_trees()
            self.modele.read_all()

            self._read_dclm()
            self._read_dlhy()
            self._read_ocal()

        self.was_read = True

    def renommer(self, nom_scenario_cible, folder):
        """
        Renommer le scénario courant

        :param nom_scenario_cible: nouveau nom du scénario
        :type nom_scenario_cible: str
        :param folder: dossier pour les fichiers XML
        :type folder: str
        """
        self.id = nom_scenario_cible
        for xml_type in Scenario.FILES_XML:
            self.files[xml_type] = os.path.join(folder, nom_scenario_cible[3:] + '.' + xml_type + '.xml')

    def remove_run(self, run_id):
        """
        Supprimer un run

        :param run_id: nom du run à supprimer
        """
        run_path = os.path.join(self.get_run(run_id).run_mo_path, '..')
        logger.debug("Suppression du Run #%s (%s)" % (run_id, run_path))
        del self.runs[run_id]
        if os.path.exists(run_path):
            shutil.rmtree(run_path)

    def remove_all_runs(self, sleep=0.0):
        """
        Supprimer tous les Runs existants

        :param sleep: temps d'attente (en secondes)
        :type sleep: float
        """
        for run_id in self.get_liste_run_ids():
            self.remove_run(run_id)
        if sleep > 0.0:  # Avoid potential conflict if folder is rewritten directly afterwards
            time.sleep(sleep)

    def create_new_run(self, etude, run_id=None, comment='', force=False):
        """
        Description détaillée:
            Créer un nouveau dossier de Run
            L'instance de `etude` est modifiée mais le fichier etu.xml n'est pas mis à jour
            (Si nécessaire, cela doit être fait après en appelant la méthode spécifique)

            1) Création d'un nouveau run (sans enregistrer la mise à jour du fichier etu.xml en entrée)
            2) Ecriture des fichiers XML dans un nouveau dossier du run

            Même comportement que Fudaa-Crue :

            - Dans le fichier etu.xml:

                - on conserve la liste des Runs précédents (sans copier les fichiers)
                - on conserve les Sm/Mo/Sc qui sont hors du Sc courant

            - Seuls les XML du scénario courant sont écrits dans le dossier du run
            - Les XML du modèle associés sont écrits dans un sous-dossier
            - Les données géographiques (fichiers shp) des sous-modèles ne sont pas copiées

        :param etude: étude courante
        :type etude: Etude
        :param run_id: nom du Run (si vide alors son nom correspondra à l'horodatage)
        :type run_id: str
        :param comment: commentaire du Run
        :type comment: str
        :param force: écraser le Run s'il existe déjà
        :type force: bool
        :return: run non lancé
        :rtype: Run
        """
        if not self.was_read:
            raise ExceptionCrue10("L'appel à read_all doit être fait pour %s" % self)

        # Create a Run instance
        if run_id is None:
            run_id = get_run_identifier()
        if len(run_id) > 32:
            raise ExceptionCrue10("Le nom du Run dépasse 32 caractères: `%s`" % run_id)
        run_folder = os.path.join(etude.folder, etude.folders['RUNS'], self.id, run_id)
        run = Run(os.path.basename(etude.etu_path), os.path.join(run_folder, self.modele.id),
                  metadata={'Commentaire': comment})

        if not force:
            if os.path.exists(run_folder):
                raise ExceptionCrue10("Le dossier du Run `%s` existe déjà. "
                                      "Utilisez l'argument force=True si vous souhaitez le supprimer" % run_id)
        elif run.id in self.runs:
            self.remove_run(run.id)

        # Check that run_id is unique in current study
        if run_id in etude.get_liste_run_names():
            raise ExceptionCrue10("Le Run `%s` existe déjà dans l'étude" % run_id)

        self.ajouter_run(run)
        self.set_current_run_id(run.id)

        # Update etude attribute
        etude.nom_scenario_courant = self.id

        # Write files and create folder is necessary
        logger.debug("Écriture du %s dans %s" % (run, run_folder))
        mo_folder = os.path.join(run_folder, self.modele.id)
        self.write_all(run_folder, folder_config=None, write_model=False)
        self.modele.write_all(mo_folder, folder_config=None)
        etude.write_etu(run_folder)

        # Write xxcprovx.dat for Crue9
        # xxcprovx_path = os.path.join(mo_folder, 'xxcprovx.dat')
        # folder_to_write = mo_folder #+ '\\' + os.path.basename(mo_folder)
        # with open(xxcprovx_path, 'w') as out:
        #     out.write(" 0\n")
        #     out.write("Q:\\Qualif_Exec\\Crue9.3\\francais\n")
        #     out.write(folder_to_write + '\n')
        #     out.write(folder_to_write + '\n')

        return run

    def create_and_launch_new_run(self, etude, run_id=None, exe_path=CRUE10_EXE_PATH, comment='', force=False):
        """
        Créer et lancer un nouveau run

        :param etude: étude courante
        :type etude: Etude
        :param run_id: nom du Run (si vide alors son nom correspondra à l'horodatage)
        :type run_id: str
        :param exe_path: chemin vers l'exécutable crue10.exe
        :type exe_path: str
        :param comment: commentaire du Run
        :type comment: str
        :param force: écraser le Run s'il existe déjà
        :type force: bool
        """
        run = self.create_new_run(etude, run_id=run_id, comment=comment, force=force)
        run.launch_services(Run.SERVICES, exe_path=exe_path)
        return run

    def create_and_launch_new_multiple_sequential_runs(self, modifications_liste, etude,
                                                       exe_path=CRUE10_EXE_PATH, force=False):
        """
        Créer et lancer des runs séquentiels selon les modifications demandées

        :param modifications: liste avec les dictionnaires contenant les modifications
        :type modifications: list(dict(str))
        :param etude: étude courante
        :type etude: Etude
        :param exe_path: chemin vers l'exécutable crue10.exe
        :type exe_path: str
        :param force: écraser le Run s'il existe déjà
        :type force: bool
        :return: liste des runs lancés
        :rtype: list(Run)
        """
        etude.ignore_others_scenarios(self.id)
        run_liste = []
        for modifications in modifications_liste:
            curr_scenario = deepcopy(self)
            run_id = modifications.pop('run_id')
            try:
                comment = modifications.pop('comment')
            except KeyError:
                comment = ''
            curr_scenario.apply_modifications(modifications)

            run = curr_scenario.create_new_run(etude, run_id=run_id, comment=comment, force=force)
            run.launch_services(Run.SERVICES, exe_path=exe_path)
            run_liste.append(run)
        return run_liste

    def _write_dclm(self, folder):
        """
        Écrire le fichier dclm.xml

        :param folder: dossier de sortie
        """
        self._write_xml_file(
            'dclm', folder,
            isinstance=isinstance,
            CalcPseudoPerm=CalcPseudoPerm,
            CalcTrans=CalcTrans,
            calculs=self.calculs,
        )

    def _write_dlhy(self, folder):
        """
        Écrire le fichier dlhy.xml

        :param folder: dossier de sortie
        """
        self._write_xml_file(
            'dlhy', folder,
            loi_hydraulique_liste=[loi for _, loi in self.lois_hydrauliques.items()],
        )

    def _write_ocal(self, folder):
        """
        Écrire le fichier dclm.xml

        :param folder: dossier de sortie
        """
        self._write_xml_file(
            'ocal', folder,
            sorties=self.ocal_sorties,
            liste_ord_calc_pseudoperm=self.liste_ord_calc_pseudoperm,
            liste_ord_calc_trans=self.liste_ord_calc_trans,
        )

    def write_all(self, folder, folder_config=None, write_model=True):
        """Écrire tous les fichiers du scénario"""
        logger.debug("Écriture de %s dans %s (grammaire %s)" % (self, folder, self.version_grammaire))

        # Create folder if not existing
        if not os.path.exists(folder):
            os.makedirs(folder)

        for xml_type in Scenario.FILES_XML_WITHOUT_TEMPLATE:
            xml_path = os.path.join(folder, os.path.basename(self.files[xml_type]))
            if self.xml_trees:
                write_xml_from_tree(self.xml_trees[xml_type], xml_path)
            else:
                write_default_xml_file(xml_type, self.version_grammaire, xml_path)

        self._write_dclm(folder)
        self._write_dlhy(folder)
        self._write_ocal(folder)

        if write_model:
            self.modele.write_all(folder, folder_config)

    def changer_grammaire(self, version_grammaire):
        """
        Changer la version de grammaire

        :param version_grammaire: version cible de la grammaire
        :type version_grammaire: str
        """
        super().changer_version_grammaire(version_grammaire)
        self.modele.changer_grammaire(version_grammaire)

    def normalize_for_10_2(self):  # HARDCODED to support g1.2.1 ?
        """
        Normaliser le scénario pour Crue v10.2 : supprime quelques variables si elles sont présentes dans le ores
        """
        variables_to_remove = ['Cr', 'J', 'Jf', 'Kact_eq', 'KmajD', 'KmajG', 'Kmin',
                               'Pact', 'Rhact', 'Tauact', 'Ustaract']
        tree = self.xml_trees['ores']
        elt_section = tree.find(PREFIX + 'OrdResSections').find(PREFIX + 'OrdResSection')
        for elt_dde in elt_section:
            if elt_dde.get('NomRef') in variables_to_remove:
                elt_section.remove(elt_dde)

    def get_clim_values_from_all_calc_pseudoperm(self, nom_noeud, delta_t):
        """
        Extraction des valeurs imposées à un noeud sous forme de chronique temporelle

        :param nom_noeud: nom du noeud sur lequel extraire la chronique temporelle
        :type nom_noeud: str
        :param delta_t: durée entre 2 calculs pseudo-permanents
        :type delta_t: float
        :return: 2D-array
        """
        res = []
        for i, calcul in enumerate(self.calculs):
            if isinstance(calcul, CalcPseudoPerm):
                res.append([i * delta_t, calcul.get_valeur(nom_noeud)])
            else:
                break  # No CalcPseudoPerm possible afterwards
        return np.array(res)

    def convert_all_calc_pseudoperm_to_trans(self, delta_t, nom_calcul='Cc_T01'):
        """
        Convertir tous les calculs pseudo-permanents en un calcul transitoire
        (le premier calcul permanent est conservé car il faut en avoir un pour démarrer le transitoire)

        :param delta_t: durée entre 2 calculs pseudo-permanents
        :type delta_t: float
        :param nom_calcul: nom du calcul transitoire à créer
        :type nom_calcul: str
        """
        if not all([isinstance(calcul, CalcPseudoPerm) for calcul in self.calculs]):
            raise ExceptionCrue10("Tous les calculs ne sont pas permanents")
        if len(self.calculs) < 2:
            raise ExceptionCrue10("Il faut au moins 2 calculs permanents")

        # Ajout des lois hydrauliques
        calcul = self.calculs[0]
        nom_lois = []
        duree_float = 0.0
        for values in calcul.values:
            nom_emh, clim_tag, is_active, value, sens, typ_loi, param_loi, nom_fic = values
            if typ_loi == 'Zimp':
                loi_type = 'LoiTZimp'
            elif typ_loi == 'Qapp':
                loi_type = 'LoiTQapp'
            else:
                raise NotImplementedError("Le type de loi n'est pas convertible : %s" % typ_loi)
            nom_loi = loi_type + '_' + nom_emh
            nom_lois.append(nom_loi)
            loi_hydraulique = LoiHydraulique(nom_loi, loi_type)
            values = self.get_clim_values_from_all_calc_pseudoperm(nom_emh, delta_t)
            duree_float = max(duree_float, values[-1, 0])
            loi_hydraulique.set_values(values)
            self.ajouter_loi_hydraulique(loi_hydraulique)

        # Création du calcul transitoire
        new_calcul = CalcTrans(nom_calcul)

        for values, nom_loi in zip(calcul.values, nom_lois):
            nom_emh, clim_tag, is_active, value, sens, typ_loi, param_loi, nom_fic = values
            loi = self.get_loi_hydraulique(nom_loi)

            # Change clim_tag for unsteady calculation
            if loi.type == 'LoiTZimp':
                clim_tag = 'CalcTransNoeudNiveauContinuLimnigramme'
            elif loi.type == 'LoiTQapp':
                clim_tag = 'CalcTransNoeudQapp'
            else:
                raise NotImplementedError
            typ_loi = CalcTrans.CLIM_TYPE_TO_TAG_VALUE[clim_tag]

            new_calcul.ajouter_valeur(nom_emh, clim_tag, is_active, nom_loi, sens, typ_loi, param_loi, nom_fic)

        # Mise à jour de la liste des calculs
        self.calculs = [calcul, new_calcul]
        self.liste_ord_calc_pseudoperm = [OrdCalcPseudoPerm(calcul.id, ('IniCalcCI', None), None)]
        self.liste_ord_calc_trans = [OrdCalcTrans(new_calcul.id, duree_float, self.modele.get_pnum_CalcTrans_PdtCst(),
                                                  ('IniCalcPrecedent', None), None, None)]

    def __repr__(self):
        return "Scénario %s" % self.id
