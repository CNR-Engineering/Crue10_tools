# coding: utf-8
from builtins import super  # Python2 fix
from collections import OrderedDict
from copy import deepcopy
import os.path
import shutil
import subprocess
import time

from crue10.base import FichierXML
from crue10.modele import Modele
from crue10.run import get_run_identifier, Run
from crue10.utils import check_isinstance, check_preffix, ExceptionCrue10, get_optional_commentaire, \
    logger, PREFIX, write_default_xml_file, write_xml_from_tree
from crue10.utils.settings import CRUE10_EXE_PATH, CRUE10_EXE_OPTS
from .calcul import Calcul, CalcPseudoPerm, CalcTrans


class Scenario(FichierXML):
    """
    Crue10 scenario
    - id <str>: scenario identifier
    - modele <[Modele]>: modele
    - runs <[Runs]>: runs
    - current_run_id <str>: current run identifier
    """

    FILES_XML = ['ocal', 'ores', 'pcal', 'dclm', 'dlhy']
    FILES_XML_WITHOUT_TEMPLATE = ['ocal', 'ores', 'pcal', 'dlhy']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, scenario_name, modele, access='r', files=None, metadata=None):
        """
        :param scenario_name: scenario name
        :param modele: a Modele instance
        :param files: dict with xml path files
        :param metadata: dict containing metadata
        """
        check_preffix(scenario_name, 'Sc_')
        self.id = scenario_name
        super().__init__(access, files, metadata)

        self.calculs = []

        self.modele = None
        self.set_modele(modele)

        self.current_run_id = None
        self.runs = OrderedDict()

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

    def add_run(self, run):
        check_isinstance(run, Run)
        if run.id in self.runs:
            raise ExceptionCrue10("Le Run %s est déjà présent" % run.id)
        self.runs[run.id] = run

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

    def set_modele(self, modele):
        check_isinstance(modele, Modele)
        self.modele = modele

    def set_current_run_id(self, run_id):
        if run_id not in self.runs:
            raise ExceptionCrue10("Le Run '%s' n'existe pas" % run_id)
        self.current_run_id = run_id

    def apply_modifications(self, modifications):
        """
        Modifie le scénario courant à partir d'un dictionnaire décrivant les modifications

        Les modifications possibles sont :

        # Sur le scénario ou modèle
        - `pnum.CalcPseudoPerm.Pdt`: <float> => affection du pas de temps (en secondes) pour les calculs permanents
        - `Qapp_factor.NomNoeud`: <float> => application du facteur multiplicatif
              à tous les débits imposés au noeud nommé NomNoeur

        # Sur les sous-modèles
        - `Fk_NomLoi`: <float> => modification du Strickler de la loi de frottement nommée NomLoi
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
            elif modification_key.startswith('Fk_'):
                loi = self.modele.get_loi_frottement(modification_key)
                loi.set_loi_Fk_values(modification_value)
            elif modification_key.startswith('Qapp_factor.'):
                nom_noeud = modification_key[12:]
                for calcul in self.get_liste_calc_pseudoperm():
                    calcul.multiplier_valeur(nom_noeud, modification_value)
            else:
                raise ExceptionCrue10("La modification `%s` n'est pas reconnue. "
                                      "Voyez la documentation de Scenario.apply_modifications" % modification_key)

    def _read_dclm(self):
        """
        Read dclm.xml file
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

                    calc_perm.ajouter_valeur(
                        elt_valeur.get('NomRef'),
                        clim_type,
                        elt_valeur.find(PREFIX + 'IsActive').text == 'true',
                        value,
                        sens,
                    )

                self.ajouter_calcul(calc_perm)

            if elt_calc.tag == PREFIX + 'CalcTrans':
                calc_trans = CalcTrans(elt_calc.get('Nom'), get_optional_commentaire(elt_calc))
                for elt_valeur in elt_calc:
                    if elt_valeur.tag == (PREFIX + 'Commentaire'):
                        continue

                    clim_type = elt_valeur.tag[len(PREFIX):]
                    if clim_type not in CalcTrans.CLIM_TYPE_TO_TAG_VALUE:
                        raise ExceptionCrue10("Type de Clim inconnu: %s" % clim_type)

                    if clim_type == 'CalcTransBrancheOrificeManoeuvre':
                        sens = elt_valeur.find(PREFIX + 'SensOuv').text
                    else:
                        sens = None

                    value_elt = elt_valeur.find(PREFIX + CalcTrans.CLIM_TYPE_TO_TAG_VALUE[clim_type])
                    nom_loi = value_elt.get('NomRef')  # TODO: check law exists

                    calc_trans.ajouter_valeur(
                        elt_valeur.get('NomRef'),
                        clim_type,
                        elt_valeur.find(PREFIX + 'IsActive').text == 'true',
                        nom_loi,
                        sens,
                    )

                self.ajouter_calcul(calc_trans)

    def read_all(self):
        if not self.was_read:
            self._set_xml_trees()
            self.modele.read_all()
            self._read_dclm()

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

    def create_and_launch_new_run(self, etude, run_id=None, exe_path=None, comment='', force=False):
        """
        Create and launch a new run
             The instance of `etude` is modified but the original etu file not overwritten
             (If necessary, it should be done after calling this method)

        1) Création d'un nouveau run (sans enregistrer la mise à jour du fichier etu.xml en entrée)
        2) Ecriture des fichiers XML dans un nouveau dossier du run
        3) Lancement de crue10.exe en ligne de commande

        Même comportement que Fudaa-Crue :
        - Dans le fichier etu.xml:
            - on conserve la liste des Runs précédents (sans copier les fichiers)
            - on conserve les Sm/Mo/Sc qui sont hors du Sc courant
        - Seuls les XML du scénario courant sont écrits dans le dossier du run
        - Les XML du modèle associés sont écrits dans un sous-dossier
        - Les données géographiques (fichiers shp) des sous-modèles ne sont pas copiées
        """
        if not self.was_read:
            raise ExceptionCrue10("L'appel à read_all doit être fait pour %s" % self)
        if exe_path is None:
            exe_path = CRUE10_EXE_PATH
        if not os.path.exists(exe_path) and exe_path.endswith('.exe'):
            raise ExceptionCrue10("Le chemin vers l'exécutable n'existe pas : `%s`" % exe_path)

        # Create a Run instance
        if run_id is None:
            run_id = get_run_identifier()
        if len(run_id) > 32:
            raise ExceptionCrue10("Le nom du Run dépasse 32 caractères: `%s`" % run_id)
        run_folder = os.path.join(etude.folder, etude.folders['RUNS'], self.id, run_id)
        run = Run(os.path.join(run_folder, self.modele.id), metadata={'Commentaire': comment})

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

        # Run crue10.exe in command line and redirect stdout and stderr in csv files
        etu_path = os.path.join(run_folder, os.path.basename(etude.etu_path))
        cmd_list = [exe_path] + CRUE10_EXE_OPTS + [etu_path]
        logger.info("Éxécution : %s" % ' '.join(cmd_list))
        with open(os.path.join(run_folder, 'stdout.csv'), "w") as out_csv:
            with open(os.path.join(run_folder, 'stderr.csv'), "w") as err_csv:
                exit_code = subprocess.call(cmd_list, stdout=out_csv, stderr=err_csv)
                # exit_code is always to 0 even in case of computation error
        run.read_traces()
        return run

    def _write_dclm(self, folder):
        self._write_xml_file(
            'dclm', folder,
            isinstance=isinstance,
            CalcPseudoPerm=CalcPseudoPerm,
            CalcTrans=CalcTrans,
            calculs=self.calculs,
        )

    def write_all(self, folder, folder_config=None, write_model=True):
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

        if write_model:
            self.modele.write_all(folder, folder_config)

    def normalize_for_10_2(self):
        """Remove some variables if they are present in ores"""
        variables_to_remove = ['Cr', 'J', 'Jf', 'Kact_eq', 'Pact', 'Rhact', 'Tauact', 'Ustaract']
        tree = self.xml_trees['ores']
        elt_section = tree.find(PREFIX + 'OrdResSections').find(PREFIX + 'OrdResSection')
        for elt_dde in elt_section:
            if elt_dde.get('NomRef') in variables_to_remove:
                elt_section.remove(elt_dde)

    def __repr__(self):
        return "Scénario %s" % self.id
