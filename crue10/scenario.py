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
    - comment <str>: information describing current scenario
    - model <[Model]>: model
    """

    FILES_XML = ['ocal', 'ores', 'pcal', 'dclm', 'dlhy']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, scenario_name, access='r', files=None, metadata=None, comment=''):
        check_preffix(scenario_name, 'Sc_')
        self.id = scenario_name
        self.files = files
        self.metadata = metadata
        self.comment = comment

        self.model = None

        if metadata is None:
            self.metadata['Type'] = 'Crue10'
        self.metadata = add_default_missing_metadata(self.metadata, Model.METADATA_FIELDS)

        if access == 'r':
            if files is None:
                raise RuntimeError
            if set(files.keys()) != set(Scenario.FILES_XML):
                raise RuntimeError
            self.files = files
            self.read_all()
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

    def set_model(self, model):
        check_isinstance(model, Model)
        self.model = model

    def read_all(self):
        # TODO: Reading of ['ocal', 'ores', 'pcal', 'dclm', 'dlhy'] is not supported yet!
        self.model.read_all()

    def _write_default_file(self, xml_type, file_path):
        shutil.copyfile(os.path.join(XML_DEFAULT_FOLDER, xml_type + '.xml'), file_path)

    def write_all(self, folder):
        logger.debug("Writing %s in %s" % (self, folder))

        for xml_type in Scenario.FILES_XML:
            self._write_default_file(xml_type, os.path.join(folder, self.files[xml_type]))

        self.model.write_all(folder)

    def __repr__(self):
        return "Scénario %s" % self.id
