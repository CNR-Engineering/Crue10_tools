# coding: utf-8
from lxml import etree
import os.path
import xml.etree.ElementTree as ET

from crue10.submodel import SubModel
from crue10.utils import CrueError, logger, PREFIX


XSD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'crue10', 'data', 'xsd')


class Study:
    """
    Crue10 study
    - etu_path <str>: path to etu.xml file
    - files <[str]>: list of xml files
    - submodels <{str: SubModel}>: dict with submodel name and SubModel object
    """
    def __init__(self, etu_path):
        self.etu_path = etu_path
        self.files = []
        self.submodels = {}
        self.read_etu()

    def read_etu(self):
        root = ET.parse(self.etu_path).getroot()
        folder = os.path.dirname(self.etu_path)

        # FichEtudes
        fichiers = root.find(PREFIX + 'FichEtudes')
        for fichier in fichiers:
            self.files.append(os.path.join(folder, fichier.get('Nom')))

        # SousModeles
        sous_modeles = root.find(PREFIX + 'SousModeles')
        for sous_modele in sous_modeles:
            files = {}
            submodel_name = sous_modele.get('Nom')

            fichiers = sous_modele.find(PREFIX + 'SousModele-FichEtudes')
            for ext in SubModel.FILES_XML:
                try:
                    filename = fichiers.find(PREFIX + ext.upper()).attrib['NomRef']
                except AttributeError:
                    raise CrueError("Le fichier %s n'est pas renseigné dans le sous-modèle !" % ext)
                if filename is None:
                    raise CrueError("Le sous-modèle n'a pas de fichier %s !" % ext)
                filepath = os.path.join(folder, filename)
                if filepath not in self.files:
                    raise CrueError("Le fichier %s n'est pas dans la liste des fichiers !" % filepath)
                files[ext] = filepath

            for shp_name in SubModel.FILES_SHP:
                files[shp_name] = os.path.join(folder, 'Config', submodel_name.upper(), shp_name + '.shp')
            submodel = SubModel(submodel_name, files)
            self.submodels[submodel.id] = submodel

    def get_submodel(self, submodel_name):
        try:
            return self.submodels[submodel_name]
        except KeyError:
            raise CrueError("Le sous-modèle %s n'existe pas  !\nLes noms possibles sont: %s"
                            % (submodel_name, list(self.submodels.keys())))

    def check_xml_files(self):
        errors = {}
        for file in self.files:
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
