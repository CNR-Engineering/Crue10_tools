# coding: utf-8
from collections import OrderedDict
from lxml import etree
import os.path
import xml.etree.ElementTree as ET

from crue10.model import Model
from crue10.scenario import Scenario
from crue10.submodel import SubModel
from crue10.utils import add_default_missing_metadata, check_isinstance, CrueError, JINJA_ENV, \
    logger, PREFIX, XML_ENCODING, XSD_FOLDER


class Study:
    """
    Crue10 study
    - etu_path <str>: path to etu.xml file
    - access <str>: 'r' to read and 'w' to write
    - folders <{str}>: dict with folders (keys correspond to `FOLDERS` list)
    - filename_list <[str]>: list of xml file names
    - metadata <{dict}>: containing metadata (keys correspond to `METADATA_FIELDS` list)
    - current_scenario <str>: current scenario
    - comment <str>: information describing current study
    - scenarios <{str: Scenario}>: dict with scneario name and Scenario object
    - models <{str: Model}>: dict with model name and Model object
    - submodels <{str: SubModel}>: dict with submodel name and SubModel object
    """

    FOLDERS = OrderedDict([('CONFIG', 'Config'), ('FICHETUDES', '.'),
                           ('RAPPORTS', 'Rapports'), ('RUNS', 'Runs')])
    XML_FILES = Scenario.FILES_XML + Model.FILES_XML + SubModel.FILES_XML
    METADATA_FIELDS = ['Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif', 'DateDerniereModif']

    def __init__(self, etu_path, folders=None, access='r', metadata=None, comment=''):
        """
        :param etu_path: Crue10 study file (etu.xml format)
        """
        self.etu_path = etu_path
        self.access = access
        if folders is None:
            self.folders = Study.FOLDERS
        else:
            if set(folders.keys()) != set(Study.FOLDERS.keys()):
                raise RuntimeError
            if folders['FICHETUDES'] != '.':
                raise NotImplementedError
            self.folders = folders
        self.filename_list = []
        self.metadata = {} if metadata is None else metadata
        self.current_scenario = ''
        self.comment = comment

        self.scenarios = OrderedDict()
        self.models = OrderedDict()
        self.submodels = OrderedDict()

        self.metadata = add_default_missing_metadata(self.metadata, Study.METADATA_FIELDS)

        if access == 'r':
            self._read_etu()
        elif access == 'w':
            pass
        else:
            raise NotImplementedError

    @property
    def folder(self):
        return os.path.dirname(self.etu_path)

    def _read_etu(self):
        root = ET.parse(self.etu_path).getroot()
        folder = os.path.dirname(self.etu_path)

        # Study metadata
        self.metadata = {}
        for field in Study.METADATA_FIELDS:
            text = root.find(PREFIX + field).text
            self.metadata[field] = '' if text is None else text

        if root.find(PREFIX + 'ScenarioCourant'):
            self.current_scenario = root.find(PREFIX + 'ScenarioCourant').get('NomRef')

        # Repertoires
        repertoires = root.find(PREFIX + 'Repertoires')
        for repertoire in repertoires:
            self.folders[repertoire.get('Nom')] = repertoire.find(PREFIX + 'path').text

        # FichEtudes
        fichiers = root.find(PREFIX + 'FichEtudes')
        for fichier in fichiers:
            if fichier.get('Type').lower() in Study.XML_FILES:  # Ignore Crue9 files
                if fichier.get('Chemin') != '.\\':
                    raise NotImplementedError
                self.filename_list.append(os.path.join(folder, fichier.get('Nom')))

        # SousModeles
        sous_modeles = root.find(PREFIX + 'SousModeles')
        for sous_modele in sous_modeles:
            files = {}
            submodel_name = sous_modele.get('Nom')

            metadata = {}
            for field in SubModel.METADATA_FIELDS:
                text = sous_modele.find(PREFIX + field).text
                metadata[field] = '' if text is None else text

            fichiers = sous_modele.find(PREFIX + 'SousModele-FichEtudes')
            for ext in SubModel.FILES_XML:
                try:
                    filename = fichiers.find(PREFIX + ext.upper()).attrib['NomRef']
                except AttributeError:
                    raise CrueError("Le fichier %s n'est pas renseigné dans le sous-modèle !" % ext)
                if filename is None:
                    raise CrueError("Le sous-modèle n'a pas de fichier %s !" % ext)
                filepath = os.path.join(folder, filename)
                if filepath not in self.filename_list:
                    raise CrueError("Le fichier %s n'est pas dans la liste des fichiers !" % filepath)
                files[ext] = filepath

            for shp_name in SubModel.FILES_SHP:
                files[shp_name] = os.path.join(folder, self.folders['CONFIG'],
                                               submodel_name.upper(), shp_name + '.shp')

            submodel = SubModel(submodel_name, files=files, metadata=metadata)
            self.add_submodel(submodel)
        if not self.submodels:
            raise CrueError("Il faut au moins un sous-modèle !")

        # Modele
        modeles = root.find(PREFIX + 'Modeles')
        for scenario in modeles:
            if scenario.tag == PREFIX + 'Modele':  # Ignore Crue9 models
                files = {}
                model_name = scenario.get('Nom')

                metadata = {}
                for field in Model.METADATA_FIELDS:
                    text = scenario.find(PREFIX + field).text
                    metadata[field] = '' if text is None else text

                fichiers = scenario.find(PREFIX + 'Modele-FichEtudes')
                for ext in Model.FILES_XML:
                    try:
                        filename = fichiers.find(PREFIX + ext.upper()).attrib['NomRef']
                    except AttributeError:
                        raise CrueError("Le fichier %s n'est pas renseigné dans le modèle !" % ext)
                    if filename is None:
                        raise CrueError("Le modèle n'a pas de fichier %s !" % ext)
                    filepath = os.path.join(folder, filename)
                    if filepath not in self.filename_list:
                        raise CrueError("Le fichier %s n'est pas dans la liste des fichiers !" % filepath)
                    files[ext] = filepath

                model = Model(model_name, files=files, metadata=metadata)

                sous_modeles = scenario.find(PREFIX + 'Modele-SousModeles')
                for sous_modele in sous_modeles:
                    submodel_name = sous_modele.get('NomRef')
                    submodel = self.submodels[submodel_name]
                    model.add_submodel(submodel)

                self.add_model(model)
        if not self.models:
            raise CrueError("Il faut au moins un modèle !")

        # Scenarios
        scenarios = root.find(PREFIX + 'Scenarios')
        for scenario in scenarios:
            if scenario.tag == PREFIX + 'Scenario':
                files = {}
                scenario_name = scenario.get('Nom')

                metadata = {}
                for field in Scenario.METADATA_FIELDS:
                    text = scenario.find(PREFIX + field).text
                    metadata[field] = '' if text is None else text

                fichiers = scenario.find(PREFIX + 'Scenario-FichEtudes')
                for ext in Scenario.FILES_XML:
                    try:
                        filename = fichiers.find(PREFIX + ext.upper()).attrib['NomRef']
                    except AttributeError:
                        raise CrueError("Le fichier %s n'est pas renseigné dans le scénario !" % ext)
                    if filename is None:
                        raise CrueError("Le scénario n'a pas de fichier %s !" % ext)
                    filepath = os.path.join(folder, filename)
                    if filepath not in self.filename_list:
                        raise CrueError("Le fichier %s n'est pas dans la liste des fichiers !" % filepath)
                    files[ext] = filepath

                modeles = scenario.find(PREFIX + 'Scenario-Modeles')
                model = None
                for i, modele in enumerate(modeles):
                    model = self.models[modele.get('NomRef')]
                    if i != 0:
                        raise NotImplementedError  # A single Model for a Scenario!

                sc = Scenario(scenario_name, model, files=files, metadata=metadata)
                self.add_scenario(sc)
        if not self.scenarios:
            raise CrueError("Il faut au moins un scénario !")

    def read_all(self):
        # self._read_etu() is done in `__init__` method
        for _, scenario in self.scenarios.items():
            scenario.read_all()

    def _write_etu(self, folder):
        xml = 'etu'
        template_render = JINJA_ENV.get_template(xml + '.xml').render(
            folders=[(name, folder) for name, folder in self.folders.items()],
            metadata=self.metadata,
            current_scenario=self.current_scenario,
            files=[(os.path.basename(file), file[-8:-4].upper()) for file in sorted(self.filename_list)],
            models=[mo for _, mo in self.models.items()],
            submodels=[sm for _, sm in self.submodels.items()],
            scenarios=[sc for _, sc in self.scenarios.items()],
        )
        with open(os.path.join(folder, os.path.basename(self.etu_path)), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

    def write_all(self, folder=None):
        folder = self.folder if folder is None else folder
        logger.debug("Writing %s in %s" % (self, folder))

        # Create folder if not existing
        if not os.path.exists(folder):
            os.makedirs(folder)

        self._write_etu(folder)
        for _, scenario in self.scenarios.items():
            scenario.write_all(folder, self.folders['CONFIG'])

    def add_files(self, file_list):
        for file in file_list:
            if file not in self.filename_list:
                self.filename_list.append(file)

    def add_model(self, model):
        check_isinstance(model, Model)
        self.add_files([file for _, file in model.files.items()])
        for submodel in model.submodels:
            self.add_submodel(submodel)
        self.models[model.id] = model

    def add_submodel(self, submodel):
        check_isinstance(submodel, SubModel)
        self.add_files([file for _, file in submodel.files.items() if file[-8:-4] in SubModel.FILES_XML])
        self.submodels[submodel.id] = submodel

    def add_scenario(self, scenario):
        check_isinstance(scenario, Scenario)
        self.add_files([file for _, file in scenario.files.items()])
        self.add_model(scenario.model)
        self.scenarios[scenario.id] = scenario

    def create_empty_scenario(self, scenario_name, model_name, submodel_name, comment=''):
        submodel = SubModel(submodel_name, access=self.access, metadata={'Commentaire': comment})
        model = Model(model_name, access=self.access, metadata={'Commentaire': comment})
        model.add_submodel(submodel)
        scenario = Scenario(scenario_name, model, access=self.access, metadata={'Commentaire': comment})
        self.add_scenario(scenario)
        if not self.current_scenario:
            self.current_scenario = scenario.id

    def get_scenario(self, scenario_name):
        try:
            return self.scenarios[scenario_name]
        except KeyError:
            raise CrueError("Le scénario %s n'existe pas  !\nLes noms possibles sont: %s"
                            % (scenario_name, list(self.scenarios.keys())))

    def get_model(self, model_name):
        try:
            return self.models[model_name]
        except KeyError:
            raise CrueError("Le modèle %s n'existe pas  !\nLes noms possibles sont: %s"
                            % (model_name, list(self.models.keys())))

    def get_submodel(self, submodel_name):
        try:
            return self.submodels[submodel_name]
        except KeyError:
            raise CrueError("Le sous-modèle %s n'existe pas  !\nLes noms possibles sont: %s"
                            % (submodel_name, list(self.submodels.keys())))

    def check_xml_files(self):
        errors = {}
        for file in self.filename_list:
            errors[file] = []
            file_splitted = file.split('.')
            if len(file_splitted) > 2:
                xml_type = file_splitted[-2]
                xsd_tree = etree.parse(os.path.join(XSD_FOLDER, '%s-1.2.xsd' % xml_type))

                with open(file, 'r', encoding='utf-8') as in_xml:
                    content = '\n'.join(in_xml.readlines())
                    xmlschema = etree.XMLSchema(xsd_tree)
                    try:
                        xml_tree = etree.fromstring(content)
                        try:
                            xmlschema.assertValid(xml_tree)
                        except etree.DocumentInvalid as e:
                            errors[file].append('Invalid XML: %s' % e)
                    except etree.XMLSyntaxError as e:
                        errors[file].append('Error XML: %s' % e)
        return errors

    def summary(self):
        return "%s: %i scénario(s) %i modèle(s), %i sous-modèle(s)" % (self, len(self.scenarios),
                                                                       len(self.models), len(self.submodels))

    def __repr__(self):
        return "Étude %s" % os.path.basename(self.etu_path[:-8])
