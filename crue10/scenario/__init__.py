# coding: utf-8
from builtins import super  # Python2 fix
from collections import OrderedDict
from copy import deepcopy
import os.path
import shutil
import time

from crue10.base import FichierXML
from crue10.modele import Modele
from crue10.run import get_run_identifier, Run
from crue10.utils import check_isinstance, check_preffix, duration_iso8601_to_seconds, duration_seconds_to_iso8601, \
    ExceptionCrue10, get_optional_commentaire, \
    logger, parse_loi, PREFIX, write_default_xml_file, write_xml_from_tree
from crue10.utils.settings import CRUE10_EXE_PATH
from .calcul import Calcul, CalcPseudoPerm, CalcTrans
from .loi_hydraulique import LoiHydraulique


class Scenario(FichierXML):
    """
    Scénario Crue10

    :param id: nom du scénario
    :type id: str
    :param modele: modèle
    :type modele: Modele
    :param calculs: liste des calculs
    :type calculs: [Calcul]
    :param lois_hydrauliques: dictionnaire des lois hydrauliques
    :type lois_hydrauliques: OrderedDict(LoiHydraulique)
    :param runs: dictionnaire des runs
    :type runs: OrderedDict(Run)
    :param current_run_id: nom du scénario courant
    :type current_run_id: str
    """

    FILES_XML = ['ocal', 'ores', 'pcal', 'dclm', 'dlhy']
    FILES_XML_WITHOUT_TEMPLATE = ['ocal', 'ores', 'pcal']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, nom_scenario, modele, access='r', files=None, metadata=None):
        """
        :param nom_scenario: scenario name
        :param modele: a Modele instance
        :param files: dict with xml path files
        :param metadata: dict containing metadata
        """
        check_preffix(nom_scenario, 'Sc_')
        self.id = nom_scenario
        super().__init__(access, files, metadata)

        self.calculs = []
        self.lois_hydrauliques = OrderedDict()

        self.modele = None
        self.set_modele(modele)

        self.current_run_id = None
        self.runs = OrderedDict()

    def _get_ocal_OrdCalcTrans(self, calc_name):
        elt = self.xml_trees['ocal'].find(PREFIX + 'OrdCalcTrans[@NomRef="%s"]' % calc_name)
        if elt is None:
            raise ExceptionCrue10("Le calcul transitoire `%s` n'est pas trouvé" % calc_name)
        return elt

    def get_ocal_OrdCalcTrans_DureeCalc(self, calc_name):
        """
        Obtenir la durée du calcul transitoire demandé

        :param calc_name: nom du calcul transitoire
        :type calc_name: str
        :return: durée du calcul (en secondes)
        :rtype: float
        """
        return duration_iso8601_to_seconds(self._get_ocal_OrdCalcTrans(calc_name).find(PREFIX + 'DureeCalc').text)

    def get_ocal_OrdCalcTrans_PdtCst(self, calc_name):
        """
        Obtenir le pas de temps de sortie du calcul transitoire demandé

        :param calc_name: nom du calcul transitoire
        :type calc_name: str
        :return: pas de temps (en secondes)
        :rtype: float
        """
        return duration_iso8601_to_seconds(self._get_ocal_OrdCalcTrans(calc_name).
                                           find(PREFIX + 'PdtRes').find(PREFIX + 'PdtCst').text)

    def get_function_apply_modifications(self, etude):
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
        check_isinstance(calcul, Calcul)
        self.calculs.append(calcul)

    def ajouter_loi_hydraulique(self, loi_hydraulique):
        check_isinstance(loi_hydraulique, LoiHydraulique)
        self.lois_hydrauliques[loi_hydraulique.id] = loi_hydraulique

    def add_run(self, run):
        check_isinstance(run, Run)
        if run.id in self.runs:
            raise ExceptionCrue10("Le Run %s est déjà présent" % run.id)
        self.runs[run.id] = run

    def get_calcul(self, nom_calcul):
        for calcul in self.calculs:
            if calcul.id == nom_calcul:
                return calcul
        raise ExceptionCrue10("Le calcul `%s` n'existe pas" % nom_calcul)

    def get_nb_calc_pseudoperm_actif(self):
        return len(self.xml_trees['ocal'].findall(PREFIX + 'OrdCalcPseudoPerm'))

    def get_nb_calc_trans_actif(self):
        return len(self.xml_trees['ocal'].findall(PREFIX + 'OrdCalcTrans'))

    def get_liste_calc_pseudoperm(self):
        return [calcul for calcul in self.calculs if isinstance(calcul, CalcPseudoPerm)]

    def get_liste_calc_trans(self):
        return [calcul for calcul in self.calculs if isinstance(calcul, CalcTrans)]

    def get_run(self, run_id):
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
        if not self.runs:
            raise ExceptionCrue10("Aucun run n'existe pour ce scénario")
        run_id = list(self.runs.keys())[-1]
        return self.get_run(run_id)

    def get_liste_run_ids(self):
        return [run_id for run_id, _ in self.runs.items()]

    def get_loi_hydraulique(self, nom_loi):
        try:
            return self.lois_hydrauliques[nom_loi]
        except KeyError:
            raise ExceptionCrue10("La loi `%s` n'existe pas" % nom_loi)

    def set_modele(self, modele):
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

        # Sur le scénario ou modèle
        - `pnum.CalcPseudoPerm.Pdt`: <float> => affection du pas de temps (en secondes) pour les calculs permanents
        - `pnum.CalcPseudoPerm.TolMaxZ`: <float> => affection de la tolérance en niveau (en m)
              pour les calculs permanents
        - `pnum.CalcPseudoPerm.TolMaxQ`: <float> => affection de la tolérance en débit (en m3/s) pour les calculs
              permanents
        - `Qapp_factor.NomCalcul.NomNoeud`: <float> => application du facteur multiplicatif au débit du
              calcul NomCalcul au noeud nommé NomNoeud
        - `Zimp.NomCalcul.NomNoeud`: <float> => application de la cote au calcul NomCalcul au noeud nommé NomNoeud
        - `branche_barrage.CoefD`: <float> => application du coefficient à la branche barrage

        # Sur les sous-modèles
        - `Fk_NomLoi`: <float> => modification du Strickler de la loi de frottement nommée NomLoi
        - `Fk_shift.*`: <float> => modification par somme du Strickler de toutes les lois de frottement (sauf celles du stockage)
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
        root = self._get_xml_root_and_set_comment('dclm')

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
        root = self._get_xml_root_and_set_comment('dlhy')

        for elt_loi in root.find(PREFIX + 'Lois'):  # LoiDF, LoiFF
            loi_hydraulique = LoiHydraulique(elt_loi.get('Nom'), elt_loi.get('Type'),
                                             comment=get_optional_commentaire(elt_loi))
            if loi_hydraulique.has_time():
                date_zero = elt_loi.find(PREFIX + 'DateZeroLoiDF').text
                if date_zero is not None:
                    loi_hydraulique.set_date_zero(date_zero)
            loi_hydraulique.set_values(parse_loi(elt_loi))
            self.ajouter_loi_hydraulique(loi_hydraulique)

    def read_all(self):
        """Lire tous les fichiers du scénario"""
        if not self.was_read:
            self._set_xml_trees()
            self.modele.read_all()

            self._read_dclm()
            self._read_dlhy()

        self.was_read = True

    def remove_run(self, run_id):
        run_path = os.path.join(self.runs[run_id].run_mo_path, '..')
        logger.debug("Suppression du Run #%s (%s)" % (run_id, run_path))
        del self.runs[run_id]
        if os.path.exists(run_path):
            shutil.rmtree(run_path)

    def remove_all_runs(self, sleep=0.0):
        """Suppression de tous les Runs existants"""
        for run_id in self.get_liste_run_ids():
            self.remove_run(run_id)
        if sleep > 0.0:  # Avoid potential conflict if folder is rewritten directly afterwards
            time.sleep(sleep)

    def create_new_run(self, etude, run_id=None, comment='', force=False):
        """
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
        :param run_id: nom du Run (si vide alors son nom correspondra à l'horodatage)
        :param comment: commentaire du Run
        :param force: écraser le Run s'il existe déjà
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

        self.add_run(run)
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
        Créé et lance un nouveau run
        """
        run = self.create_new_run(etude, run_id=run_id, comment=comment, force=force)
        run.launch_services(Run.SERVICES, exe_path=exe_path)
        return run

    def create_and_launch_new_multiple_sequential_runs(self, modifications_liste, etude, exe_path=CRUE10_EXE_PATH, force=False):
        """
        Créé et lance des runs séquentiels selon les modifications demandées
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
        Ecrire le fichier dclm.xml

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
        Ecrire le fichier dlhy.xml

        :param folder: dossier de sortie
        """
        self._write_xml_file(
            'dlhy', folder,
            loi_hydraulique_liste=[loi for _, loi in self.lois_hydrauliques.items()],
        )

    def write_all(self, folder, folder_config=None, write_model=True):
        """Écrire tous les fichiers du scénario"""
        logger.debug("Écriture de %s dans %s" % (self, folder))

        # Create folder if not existing
        if not os.path.exists(folder):
            os.makedirs(folder)

        for xml_type in Scenario.FILES_XML_WITHOUT_TEMPLATE:
            xml_path = os.path.join(folder, os.path.basename(self.files[xml_type]))
            if self.xml_trees:
                write_xml_from_tree(self.xml_trees[xml_type], xml_path)
            else:
                write_default_xml_file(xml_type, xml_path)

        self._write_dclm(folder)
        self._write_dlhy(folder)

        if write_model:
            self.modele.write_all(folder, folder_config)

    def normalize_for_10_2(self):
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

    def __repr__(self):
        return "Scénario %s" % self.id
