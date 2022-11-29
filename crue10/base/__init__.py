# coding: utf-8
import abc
from copy import deepcopy
from io import open  # Python2 fix
from lxml import etree
import os.path
import xml.etree.ElementTree as ET

from crue10.utils import add_default_missing_metadata, DATA_FOLDER_ABSPATH, ExceptionCrue10, \
    ExceptionCrue10Grammar, JINJA_ENV, get_xml_root_from_file, logger, PREFIX, XSI_SCHEMA_LOCATION
from crue10.utils.settings import VERSION_GRAMMAIRE_COURANTE, VERSION_GRAMMAIRE_PRECEDENTE, XML_ENCODING


# ABC below is compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


class EnsembleFichiersXML(ABC):
    """
    Abstract class for Crue10 XML files

    :ivar version_grammaire: version de la grammaire
    :vartype version_grammaire: str
    :ivar xml_trees: dict with XML trees (keys correspond to `FILES_XML_WITHOUT_TEMPLATE` list)
    :vartype xml_trees: {ET.ElementTree}
    :ivar metadata: containing metadata (keys correspond to `METADATA_FIELDS` list)
    :vartype metadata: {dict}
    :ivar files: dict with path to xml files (keys correspond to `FILES_XML` list)
    :vartype files: {str}
    :ivar comments: dict with comment of xml files (keys correspond to `FILES_XML` list)
    :vartype comments: {str}
    :ivar was_read: True si déjà lu
    :vartype was_read: bool
    """

    #: Fichiers XML
    FILES_XML = []

    #: Sous-fichiers XML pour Etude (l'ensemble des types composant une étude Crue10)
    SUB_FILES_XML = []

    #: Fichiers SHP pour SousModele
    FILES_SHP = []

    #: Fichiers XML sans template jinja2 (le fichier est lu/écrit par l'utilisation d'un simple parseur XML)
    FILES_XML_WITHOUT_TEMPLATE = []

    #: Nom des métadonnées présentes dans le fichier etu.xml
    METADATA_FIELDS = []

    def __init__(self, mode, files, metadata, version_grammaire=None):
        """
        L'attribut `id` doit être défini avant d'appeler cette méthode mère (super)
        """
        self.xml_trees = {}

        self.metadata = {} if metadata is None else metadata
        if 'Type' in type(self).METADATA_FIELDS:
            self.metadata['Type'] = 'Crue10'
        self.metadata = add_default_missing_metadata(self.metadata, type(self).METADATA_FIELDS)

        self.version_grammaire = version_grammaire
        if mode == 'r':
            if files is None:
                raise RuntimeError

            files_xml = deepcopy(type(self).FILES_XML)
            if version_grammaire == '1.2':  # Modele: HARDCODED to support g1.2
                try:
                    files_xml.remove('dreg')
                except ValueError:  # Etude, Scenario, SousModele
                    pass
            if set(files.keys()) != set(files_xml + type(self).FILES_SHP):
                raise RuntimeError
            self.files = files
        elif mode == 'w':
            if version_grammaire is None:
                self.version_grammaire = VERSION_GRAMMAIRE_COURANTE
            self.files = {}
            if files is None:
                for xml_type in type(self).FILES_XML:
                    if xml_type != 'etu':
                        self.files[xml_type] = self.id[3:] + '.' + xml_type + '.xml'
            else:
                self.files = files

        self.comments = {xml: '' for xml in type(self).FILES_XML}
        self.was_read = False

    @property
    def is_active(self):
        """Est actif"""
        return self.metadata['IsActive'] == 'true'

    @property
    def comment(self):
        """Commentaire"""
        return self.metadata['Commentaire']

    @property
    def file_basenames(self):
        """Retourne la liste des fichiers par type"""
        return {xml_type: os.path.basename(path) for xml_type, path in self.files.items()}

    def set_version_grammaire(self, version_grammaire):
        """
        Définir la version de la grammaire

        :param version_grammaire: version de la grammaire à définir
        :type version_grammaire: str
        """
        # Check version_grammaire consistency
        grammaires_supportees = [VERSION_GRAMMAIRE_PRECEDENTE, VERSION_GRAMMAIRE_COURANTE]
        if version_grammaire not in grammaires_supportees:
            raise ExceptionCrue10Grammar("Seules les grammaires %s sont supportées (pas `%s`)"
                                         % (grammaires_supportees, version_grammaire))
        if version_grammaire == self.version_grammaire:
            logger.warning("Changement de grammaire vers %s ignoré car %s est déjà dans cette grammaire"
                           % (self, version_grammaire))
            return  # nothing to do

        self.version_grammaire = version_grammaire

    def changer_version_grammaire(self, version_grammaire):
        """
        Changer la version de la grammaire

        :param version_grammaire: version de la grammaire cible
        :type version_grammaire: str
        """
        # Change version_grammaire in all `FILES_WITHOUT_TEMPLATE`
        for xml_type, root in self.xml_trees.items():
            old_xsi = root.get(XSI_SCHEMA_LOCATION)
            new_xsi = old_xsi.replace('-%s.xsd' % self.version_grammaire, '-%s.xsd' % version_grammaire)
            root.set(XSI_SCHEMA_LOCATION, new_xsi)

        self.set_version_grammaire(version_grammaire)

    def set_comment(self, comment):
        """Définir le commentaire"""
        self.metadata['Commentaire'] = comment

    def _get_xml_root_set_version_grammaire_and_comment(self, xml):
        try:
            root = ET.parse(self.files[xml]).getroot()
        except ET.ParseError as e:
            raise ExceptionCrue10("Erreur syntaxe XML dans `%s`:\n%s" % (self.files[xml], e))

        # Set version_grammaire
        version_grammaire = root.get(XSI_SCHEMA_LOCATION)[-7:-4]
        if self.version_grammaire is None:
            self.set_version_grammaire(version_grammaire)
        elif version_grammaire != self.version_grammaire:
            raise ExceptionCrue10Grammar("La version de la grammaire du fichier %s est %s (valeur attendue : %s)"
                                         % (xml, version_grammaire, self.version_grammaire))

        # Sets comment if the tag is found
        comment_elt = root.find(PREFIX + 'Commentaire')
        if comment_elt is not None:
            self.comments[xml] = '' if comment_elt.text is None else comment_elt.text

        return root

    def _set_xml_trees(self):
        files_xml = deepcopy(type(self).FILES_XML_WITHOUT_TEMPLATE)
        if self.version_grammaire == '1.2':  # Modele: HARDCODED to support g1.2
            try:
                files_xml.remove('dreg')
            except ValueError:  # Scenario
                pass
        for xml_type in files_xml:
            try:
                root = get_xml_root_from_file(self.files[xml_type])
            except KeyError:
                raise ExceptionCrue10("Le fichier `%s` est absent !" % xml_type)

            # Set version_grammaire
            version_grammaire = root.get(XSI_SCHEMA_LOCATION)[-7:-4]
            if self.version_grammaire is None:
                self.set_version_grammaire(version_grammaire)
            elif version_grammaire != self.version_grammaire:
                raise ExceptionCrue10Grammar(
                    "La version de la grammaire du fichier %s est %s (valeur attendue : %s)"
                    % (xml_type, version_grammaire, self.version_grammaire))

            self.xml_trees[xml_type] = root

    def _write_xml_file(self, xml, folder, **kwargs):
        template_path = self.version_grammaire + '/templates/' + xml + '.xml'  # os.path.join not working on Windows
        template_render = JINJA_ENV.get_template(template_path).render(
            comment=self.comments[xml],
            **kwargs
        )

        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

    def _check_xml_file(self, file_path):
        logger.debug("Validation XSD (grammaire %s) de %s" % (self.version_grammaire, file_path))
        errors_list = []
        file_splitted = file_path.split('.')
        if len(file_splitted) > 2:
            xml_type = file_splitted[-2]
            xsd_tree = etree.parse(os.path.join(DATA_FOLDER_ABSPATH, self.version_grammaire, 'xsd',
                                                '%s-%s.xsd' % (xml_type, self.version_grammaire)))

            with open(file_path, 'r', encoding=XML_ENCODING) as in_xml:
                content = '\n'.join(in_xml.readlines())
                xmlschema = etree.XMLSchema(xsd_tree)
                try:
                    xml_tree = etree.fromstring(content)
                    try:
                        xmlschema.assertValid(xml_tree)
                    except etree.DocumentInvalid:
                        for error in xmlschema.error_log:
                            errors_list.append("Invalid XML at line %i: %s" % (error.line, error.message))
                except etree.XMLSyntaxError as e:
                    errors_list.append('Error XML: %s' % e)
        return errors_list

    def check_xml_files(self, folder=None):
        """
        Validation XML des fichiers à leur schéma XSD

        :return: liste des erreurs
        :rtype: list(str)
        """
        if folder is None:
            filename_list = [filename for _, filename in self.files.items()]
        else:
            filename_list = [os.path.join(folder, filename) for _, filename in self.files.items()]
        errors = {}
        for file_path in filename_list:
            errors[file_path] = self._check_xml_file(file_path)
        return errors

    def log_check_xml(self, folder=None):
        """Afficher le bilan de la vérification des fichiers XML"""
        errors = self.check_xml_files(folder)
        nb_errors = 0
        for xml_file, liste_errors in errors.items():
            if liste_errors:
                logger.error("~> %i erreur(s) dans %s:" % (len(liste_errors), xml_file))
                for i, error in enumerate(liste_errors):
                    logger.error("    #%i: %s" % (i, error))
                nb_errors += len(liste_errors)
        if nb_errors == 0:
            logger.info("=> Aucune erreur dans les fichiers XML (pour %s)" % self)
        else:
            logger.error("=> %i erreur(s) dans les fichiers XML" % nb_errors)
