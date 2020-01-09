# coding: utf-8
from builtins import super  # Python2 fix
from collections import OrderedDict
import os.path
import shutil
import subprocess

from crue10.base import FichierXML
from crue10.modele import Modele
from crue10.run import get_run_identifier, Run
from crue10.utils import check_isinstance, check_preffix, CrueError, logger, \
    write_default_xml_file, write_xml_from_tree
from crue10.utils.settings import CRUE10_EXE_PATH, CRUE10_EXE_OPTS


class Scenario(FichierXML):
    """
    Crue10 scenario
    - id <str>: scenario identifier
    - modele <[Modele]>: modele
    - runs <[Runs]>: runs
    - current_run_id <str>: current run identifier
    """

    FILES_XML = ['ocal', 'ores', 'pcal', 'dclm', 'dlhy']
    FILES_XML_WITHOUT_TEMPLATE = ['ocal', 'ores', 'pcal', 'dclm', 'dlhy']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, scenario_name, model, access='r', files=None, metadata=None):
        """
        :param scenario_name: scenario name
        :param model: a Modele instance
        :param files: dict with xml path files
        :param metadata: dict containing metadata
        """
        check_preffix(scenario_name, 'Sc_')
        self.id = scenario_name
        super().__init__(access, files, metadata)

        self.modele = None
        self.set_modele(model)

        self.current_run_id = None
        self.runs = OrderedDict()

    def get_run(self, run_id):
        if not self.runs:
            raise CrueError("Aucun run n'existe pour ce scénario")
        try:
            return self.runs[run_id]
        except KeyError:
            raise CrueError("Le run %s n'existe pas !\nLes noms possibles sont: %s"
                            % (run_id, list(self.runs.keys())))

    def set_modele(self, model):
        check_isinstance(model, Modele)
        self.modele = model

    def read_all(self):
        if not self.was_read:
            self._set_xml_trees()
            self.modele.read_all()
        self.was_read = True

    def add_run(self, run):
        check_isinstance(run, Run)
        if run.id in self.runs:
            raise CrueError("Le Run %s est déjà présent" % run.id)
        self.runs[run.id] = run

    def set_current_run_id(self, run_id):
        if run_id not in self.runs:
            raise CrueError("Le Run '%s' n'existe pas" % run_id)
        self.current_run_id = run_id

    def remove_run(self, run_id, run_folder):
        del self.runs[run_id]
        run_folder = os.path.join(run_folder, self.id, run_id)
        if os.path.exists(run_folder):
            shutil.rmtree(run_folder)

    def create_and_launch_new_run(self, study, run_id=None, comment='', force=False):
        """
        Create and launch a new run
        /!\ The instance of `etude` is modified but the original etu file not overwritten
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
        # Create a Run instance
        if run_id is None:
            run_id = get_run_identifier()
        run_folder = os.path.join(study.folder, study.folders['RUNS'], self.id, run_id)
        run = Run(os.path.join(run_folder, self.modele.id), metadata={'Commentaire': comment})
        if not force:
            if os.path.exists(run_folder):
                raise CrueError("Le dossier du run existe déjà. "
                                "Utilisez l'argument force=True si vous souhaitez le supprimer")
        if run.id in self.runs:
            self.remove_run(run.id, run_folder)
        self.add_run(run)
        self.set_current_run_id(run.id)

        # Update etude attributes
        study.current_scenario_id = self.id

        # Write files and create folder is necessary
        logger.debug("Écriture de %s dans %s" % (run, run_folder))
        mo_folder = os.path.join(run_folder, self.modele.id)
        self.write_all(run_folder, folder_config=None, write_model=False)
        self.modele.write_all(mo_folder, folder_config=None)
        study.write_etu(run_folder)

        # Run crue10.exe in command line and redirect stdout and stderr in csv files
        etu_path = os.path.join(run_folder, os.path.basename(study.etu_path))
        cmd_list = [CRUE10_EXE_PATH] + CRUE10_EXE_OPTS + [etu_path]
        logger.info("Éxécution : %s" % ' '.join(cmd_list))
        with open(os.path.join(run_folder, 'stdout.csv'), "w") as out_csv:
            with open(os.path.join(run_folder, 'stderr.csv'), "w") as err_csv:
                exit_code = subprocess.call(cmd_list, stdout=out_csv, stderr=err_csv)
                logger.debug("Exit status = %i" % exit_code)
        return run.id

    def write_all(self, folder, folder_config=None, write_model=True):
        logger.debug("Écriture de %s dans %s" % (self, folder))

        # Create folder if not existing
        if not os.path.exists(folder):
            os.makedirs(folder)

        for xml_type in Scenario.FILES_XML_WITHOUT_TEMPLATE:
            xml_path = os.path.join(folder, os.path.basename(self.files[xml_type]))
            if self.xml_trees:
                write_xml_from_tree(self.xml_trees[xml_type],  xml_path)
            else:
                write_default_xml_file(xml_type, xml_path)

        if write_model:
            self.modele.write_all(folder, folder_config)

    def __repr__(self):
        return "Scénario %s" % self.id
