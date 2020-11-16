import abc
from io import open  # Python2 fix
from lxml import etree
import os.path
import xml.etree.ElementTree as ET

from crue10.utils import add_default_missing_metadata, ExceptionCrue10, JINJA_ENV, \
    get_xml_root_from_file, logger, PREFIX, XML_ENCODING, XSD_FOLDER


# ABC below is compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


class FichierXML(ABC):
    """
    Abstract class for Crue10 XML files

    :param xml_trees: dict with XML trees (keys correspond to `FILES_XML_WITHOUT_TEMPLATE` list)
    :type xml_trees: {ET.ElementTree}
    :param metadata: containing metadata (keys correspond to `METADATA_FIELDS` list)
    :type metadata: {dict}
    :param files: dict with path to xml files (keys correspond to `FILES_XML` list)
    :type files: {str}
    :param comments: dict with comment of xml files (keys correspond to `FILES_XML` list)
    :type comments: {str}
    :param was_read: True si déjà lu
    :type was_read: bool
    """

    FILES_XML = []
    FILES_XML_OPTIONAL = []
    SUB_FILES_XML = []
    FILES_SHP = []
    FILES_XML_WITHOUT_TEMPLATE = []
    METADATA_FIELDS = []

    def __init__(self, access, files, metadata):
        """
        id attribute has to be defined before calling this super method
        """
        self.xml_trees = {}

        self.metadata = {} if metadata is None else metadata
        if 'Type' in type(self).METADATA_FIELDS:
            self.metadata['Type'] = 'Crue10'
        self.metadata = add_default_missing_metadata(self.metadata, type(self).METADATA_FIELDS)

        if access == 'r':
            if files is None:
                raise RuntimeError
            if (set(files.keys()) != set(type(self).FILES_XML + type(self).FILES_XML_OPTIONAL + type(self).FILES_SHP))\
                    and (set(files.keys()) != set(type(self).FILES_XML + type(self).FILES_SHP)):
                raise RuntimeError
            self.files = files
        elif access == 'w':
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
        return self.metadata['IsActive'] == 'true'

    @property
    def comment(self):
        return self.metadata['Commentaire']

    @property
    def file_basenames(self):
        return {xml_type: os.path.basename(path) for xml_type, path in self.files.items()}

    def set_comment(self, comment):
        self.metadata['Commentaire'] = comment

    def _get_xml_root_and_set_comment(self, xml):
        try:
            root = ET.parse(self.files[xml]).getroot()
        except ET.ParseError as e:
            raise ExceptionCrue10("Erreur syntaxe XML dans `%s`:\n%s" % (self.files[xml], e))

        # Sets comment if the tag is found
        comment_elt = root.find(PREFIX + 'Commentaire')
        if comment_elt is not None:
            self.comments[xml] = '' if comment_elt.text is None else comment_elt.text

        return root

    def _set_xml_trees(self):
        for xml_type in type(self).FILES_XML_WITHOUT_TEMPLATE:
            try:
                self.xml_trees[xml_type] = get_xml_root_from_file(self.files[xml_type])
            except KeyError:
                if xml_type not in type(self).FILES_XML_OPTIONAL:
                    raise ExceptionCrue10("Le fichier `%s` est absent !" % xml_type)

    def _write_xml_file(self, xml, folder, **kwargs):
        template_render = JINJA_ENV.get_template(xml + '.xml').render(
            comment=self.comments[xml],
            **kwargs
        )

        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

    def _check_xml_file(self, file_path):
        logger.debug("Checking XSD validation on %s" % file_path)
        errors_list = []
        file_splitted = file_path.split('.')
        if len(file_splitted) > 2:
            xml_type = file_splitted[-2]
            xsd_tree = etree.parse(os.path.join(XSD_FOLDER, '%s-1.2.xsd' % xml_type))

            with open(file_path, 'r', encoding=XML_ENCODING) as in_xml:
                content = '\n'.join(in_xml.readlines())
                xmlschema = etree.XMLSchema(xsd_tree)
                try:
                    xml_tree = etree.fromstring(content)
                    try:
                        xmlschema.assertValid(xml_tree)
                    except etree.DocumentInvalid as e:
                        errors_list.append('Invalid XML: %s' % e)
                except etree.XMLSyntaxError as e:
                    errors_list.append('Error XML: %s' % e)
        return errors_list

    def check_xml_files(self, folder=None):
        if folder is None:
            filename_list = [filename for _, filename in self.files.items()]
        else:
            filename_list = [os.path.join(folder, filename) for _, filename in self.files.items()]
        errors = {}
        for file_path in filename_list:
            errors[file_path] = self._check_xml_file(file_path)
        return errors

    def log_check_xml(self, folder=None):
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
