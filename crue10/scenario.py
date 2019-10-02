# coding: utf-8
from collections import OrderedDict
import os.path
import shutil
import subprocess

from crue10.model import Model
from crue10.run import get_run_identifier, Run
from crue10.utils import add_default_missing_metadata, check_isinstance, check_preffix, CrueError, \
    get_xml_root_from_file, logger, write_default_xml_file, write_xml_from_tree
from crue10.utils.settings import CRUE10_EXE_PATH, CRUE10_EXE_OPTS


class Scenario:
    """
    Crue10 scenario
    - id <str>: scenario identifier
    - files <{str}>: dict with path to xml files (keys correspond to `FILES_XML` list)
    - xml_trees <{ET.ElementTree}>: dict with XML trees (keys correspond to `FILES_XML_WITHOUT_TEMPLATE` list)
    - metadata <{dict}>: containing metadata (keys correspond to `METADATA_FIELDS` list)
    - model <[Model]>: model
    - runs <[Runs]>: runs
    - current_run_id <str>: current run identifier
    """

    FILES_XML = ['ocal', 'ores', 'pcal', 'dclm', 'dlhy']
    FILES_XML_WITHOUT_TEMPLATE = ['ocal', 'ores', 'pcal', 'dclm', 'dlhy']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, scenario_name, model, access='r', files=None, metadata=None):
        check_preffix(scenario_name, 'Sc_')
        self.id = scenario_name
        self.files = files
        self.xml_trees = {}
        self.metadata = {} if metadata is None else metadata
        self.was_read = False

        self.model = None
        self.set_model(model)

        self.current_run_id = None
        self.runs = OrderedDict()

        self.metadata['Type'] = 'Crue10'
        self.metadata = add_default_missing_metadata(self.metadata, Scenario.METADATA_FIELDS)

        if access == 'r':
            if files is None:
                raise RuntimeError
            if set(files.keys()) != set(Scenario.FILES_XML):
                raise RuntimeError
            self.files = files
        elif access == 'w':
            self.files = {}
            if files is None:
                for xml_type in Scenario.FILES_XML:
                    self.files[xml_type] = scenario_name[3:] + '.' + xml_type + '.xml'
            else:
                raise RuntimeError

    @property
    def is_active(self):
        return self.metadata['IsActive'] == 'true'

    @property
    def comment(self):
        return self.metadata['Commentaire']

    @property
    def file_basenames(self):
        return {xml_type: os.path.basename(path) for xml_type, path in self.files.items()}

    def get_run(self, run_id):
        if not self.runs:
            raise CrueError("Aucun run n'existe pour ce scénario")
        try:
            return self.runs[run_id]
        except KeyError:
            raise CrueError("Le run %s n'existe pas !\nLes noms possibles sont: %s"
                            % (run_id, list(self.runs.keys())))

    def set_model(self, model):
        check_isinstance(model, Model)
        self.model = model

    def _set_xml_trees(self):
        for xml_type in Scenario.FILES_XML_WITHOUT_TEMPLATE:
            self.xml_trees[xml_type] = get_xml_root_from_file(self.files[xml_type])

    def read_all(self):
        if not self.was_read:
            self._set_xml_trees()
            self.model.read_all()
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

    def create_and_launch_new_run(self, study, run_id=None, comment=''):
        """
        Create and launch a new run
        /!\ The instance of `study` is modified but the original etu file not overwritten
             (If necessary, it should be done after calling this method)

        1) Création d'un nouveau run (sans mettre à jour le fichier etu.xml en entrée)
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
        run = Run(os.path.join(run_folder, self.model.id), metadata={'Commentaire': comment})
        if run.id in self.runs:
            self.remove_run(run.id, run_folder)
        self.add_run(run)
        self.set_current_run_id(run.id)

        # Update study attributes
        study.current_scenario_id = self.id

        # Write files and create folder is necessary
        logger.debug("Écriture de %s dans %s" % (run, run_folder))
        mo_folder = os.path.join(run_folder, self.model.id)
        self.write_all(run_folder, folder_config=None, write_model=False)
        self.model.write_all(mo_folder, folder_config=None)
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
            self.model.write_all(folder, folder_config)

    def __repr__(self):
        return "Scénario %s" % self.id
