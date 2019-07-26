# coding: utf-8
import os.path
import shutil

from crue10.utils import add_default_missing_metadata, check_isinstance, check_preffix, CrueError, logger, \
    XML_DEFAULT_FOLDER, XML_TEMPLATES_FOLDER

from .submodel import SubModel


class Model:
    """
    Crue10 model
    - id <str>: model identifier
    - files <{str}>: dict with path to xml files (keys correspond to `FILES_XML` list)
    - metadata <{dict}>: containing metadata (keys correspond to `METADATA_FIELDS` list)
    - comment <str>: information describing current model
    - submodels <[SubModel]>: list of submodels
    """

    FILES_XML = ['optr', 'optg', 'opti', 'pnum', 'dpti']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, model_name, access='r', files=None, metadata=None, comment=''):
        """
        :param model_name: model name
        :param files: dict with xml path files
        :param metadata: dict containing metadata
        """
        check_preffix(model_name, 'Mo_')
        self.id = model_name
        self.metadata = {} if metadata is None else metadata
        self.comment = comment
        self.was_read = False

        self.submodels = []
        # self.initial_conditions = {}
        # self.data = {}

        if 'Type' not in self.metadata:
            self.metadata['Type'] = 'Crue10'
        self.metadata = add_default_missing_metadata(self.metadata, Model.METADATA_FIELDS)

        if access == 'r':
            if files is None:
                raise RuntimeError
            if set(files.keys()) != set(Model.FILES_XML):
                raise RuntimeError
            self.files = files
        elif access == 'w':
            self.files = {}
            if files is None:
                for xml_type in Model.FILES_XML:
                    self.files[xml_type] = model_name[3:] + '.' + xml_type + '.xml'
            else:
                raise RuntimeError

    @property
    def is_active(self):
        return self.metadata['IsActive'] == 'true'

    def add_submodel(self, submodel):
        check_isinstance(submodel, SubModel)
        if submodel.id in self.submodels:
            raise CrueError("Le sous-modèle %s est déjà présent" % submodel.id)
        self.submodels.append(submodel)

    def _read_dpti(self):
        """
        Read dpti.xml file
        """
        pass  # TODO

    def read_all(self):
        if not self.was_read:
            # TODO: Reading of ['optr', 'optg', 'opti', 'pnum', 'dpti'] is not supported yet!

            for submodel in self.submodels:
                submodel.read_all()

            self._read_dpti()
        self.was_read = True

    def _write_default_file(self, xml_type, file_path):
        shutil.copyfile(os.path.join(XML_DEFAULT_FOLDER, xml_type + '.xml'), file_path)

    def write_all(self, folder):
        logger.debug("Writing %s in %s" % (self, folder))

        for xml_type in Model.FILES_XML:
            self._write_default_file(xml_type, os.path.join(folder, self.files[xml_type]))

        for submodel in self.submodels:
            submodel.write_all(folder)

    def summary(self):
        return "%s: %i sous-modèle(s)" % (self, len(self.submodels))

    def __repr__(self):
        return "Modèle %s" % self.id
