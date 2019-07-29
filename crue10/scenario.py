import os.path
import shutil

from crue10.model import Model
from crue10.utils import add_default_missing_metadata, check_isinstance, check_preffix, logger, XML_DEFAULT_FOLDER


class Scenario:
    """
    Crue10 scenario
    - id <str>: scenario identifier
    - files <{str}>: dict with path to xml files (keys correspond to `FILES_XML` list)
    - metadata <{dict}>: containing metadata (keys correspond to `METADATA_FIELDS` list)
    - model <[Model]>: model
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

    @staticmethod
    def _write_default_file(xml_type, file_path):
        shutil.copyfile(os.path.join(XML_DEFAULT_FOLDER, xml_type + '.xml'), file_path)

    def write_all(self, folder, folder_config):
        logger.debug("Writing %s in %s" % (self, folder))

        for xml_type in Scenario.FILES_XML:
            Scenario._write_default_file(xml_type, os.path.join(folder, os.path.basename(self.files[xml_type])))

        self.model.write_all(folder, folder_config)

    def __repr__(self):
        return "Scénario %s" % self.id
