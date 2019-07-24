# coding: utf-8
from .submodel import SubModel


class Model:
    """
    Crue10 model
    - id <str>: model identifier
    - submodels <[SubModel]>: list of SubModel
    """
    FILES_XML = ['optr', 'optg', 'opti', 'pnum', 'dpti']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, model_name, files, metadata):
        """
        :param model_name: model name
        :param files: dict with xml path files
        :param metadata: dict containing metadata
        """
        self.id = model_name
        self.files = files
        self.metadata = metadata

        self.submodels = []
        self.initial_conditions = {}
        self.data = {}

    @property
    def is_active(self):
        return self.metadata['IsActive'] == 'true'

    def add_submodel(self, submodel):
        if not isinstance(submodel, SubModel):
            raise RuntimeError
        self.submodels.append(submodel)

    def _read_generic_xml_file(self, file):
        pass

    def _read_dpti(self):
        """
        Read dpti.xml file
        """
        pass

    def read_all(self):
        for submodel in self.submodels:
            submodel.read_all()

        self._read_dpti()
        self._read_generic_xml_file('optr')
        self._read_generic_xml_file('optg')
        self._read_generic_xml_file('opti')
        self._read_generic_xml_file('pnum')

    def __repr__(self):
        return "Modèle %s: %i sous-modèles" % (self.id, len(self.submodels))
