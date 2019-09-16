from collections import OrderedDict
from copy import deepcopy
import os.path
import shutil
import subprocess

from crue10.model import Model
from crue10.run import Run
from crue10.utils import add_default_missing_metadata, check_isinstance, check_preffix, CrueError, \
    logger, XML_DEFAULT_FOLDER
from crue10.utils.settings import CRUE10_EXE_PATH, CRUE10_EXE_OPTS


class Scenario:
    """
    Crue10 scenario
    - id <str>: scenario identifier
    - files <{str}>: dict with path to xml files (keys correspond to `FILES_XML` list)
    - metadata <{dict}>: containing metadata (keys correspond to `METADATA_FIELDS` list)
    - model <[Model]>: model
    - runs <[Runs]>: runs
    - current_run_id <str>: current run identifier
    """

    FILES_XML = ['ocal', 'ores', 'pcal', 'dclm', 'dlhy']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, scenario_name, model, access='r', files=None, metadata=None):
        check_preffix(scenario_name, 'Sc_')
        self.id = scenario_name
        self.files = files
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

    def set_model(self, model):
        check_isinstance(model, Model)
        self.model = model

    def read_all(self):
        if not self.was_read:
            # TODO: Reading of ['ocal', 'ores', 'pcal', 'dclm', 'dlhy'] is not supported yet!

            self.model.read_all()
        self.was_read = True

    def add_run(self, run):
        check_isinstance(run, Run)
        if run.id in self.runs:
            raise CrueError("Le Run %s est déjà présent" % run.id)
        self.runs[run.id] = run

    def create_and_launch_new_run(self, study):
        """
        Create and launch a new run
        # TODO: check if not already ran before?
        """
        # Create new run instance and copy the study
        run = Run()
        # from datetime import datetime
        # run.id = datetime(2020, 1, 1).strftime("R%Y-%m-%d-%Hh%Mm%Ss")
        self.add_run(run)
        run_folder = os.path.join(study.folder, study.folders['RUNS'], self.id, run.id)
        logger.debug("Writing %s in %s" % (run, run_folder))
        self.current_run_id = run.id

        # Modified copy of the study
        out_study = deepcopy(study)
        out_study.current_scenario_id = self.id

        # Write files and create folder is necessary
        mo_folder = os.path.join(run_folder, self.model.id)
        self.write_all(run_folder, folder_config=None, write_model=False)
        self.model.write_all(mo_folder, folder_config=None)
        out_study.write_etu(run_folder)

        # Run crue10.exe in command line
        etu_path = os.path.join(run_folder, os.path.basename(study.etu_path))
        cmd_list = [CRUE10_EXE_PATH] + CRUE10_EXE_OPTS + [etu_path]
        logger.info('Running: %s' % ' '.join(cmd_list))
        call = subprocess.call(cmd_list)
        return call

    @staticmethod
    def _write_default_file(xml_type, file_path):
        shutil.copyfile(os.path.join(XML_DEFAULT_FOLDER, xml_type + '.xml'), file_path)

    def write_all(self, folder, folder_config=None, write_model=True):
        logger.debug("Writing %s in %s" % (self, folder))

        if not os.path.exists(folder):
            os.makedirs(folder)
        for xml_type in Scenario.FILES_XML:
            Scenario._write_default_file(xml_type, os.path.join(folder, os.path.basename(self.files[xml_type])))

        if write_model:
            self.model.write_all(folder, folder_config)

    def __repr__(self):
        return "Scénario %s" % self.id
