import abc
from io import open  # Python2 fix
import os.path
import xml.etree.ElementTree as ET

from crue10.utils import add_default_missing_metadata, JINJA_ENV, get_xml_root_from_file, PREFIX, XML_ENCODING


# ABC below is compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


class FichierXML(ABC):
    """
    Abstract class for Crue10 XML files

    - xml_trees <{ET.ElementTree}>: dict with XML trees (keys correspond to `FILES_XML_WITHOUT_TEMPLATE` list)
    - metadata <{dict}>: containing metadata (keys correspond to `METADATA_FIELDS` list)
    - files <{str}>: dict with path to xml files (keys correspond to `FILES_XML` list)
    - comments <{str}>: dict with comment of xml files (keys correspond to `FILES_XML` list)
    - was_read <bool>
    """
    FILES_XML = []
    FILES_SHP = []
    FILES_XML_WITHOUT_TEMPLATE = []
    METADATA_FIELDS = []

    def __init__(self, access, files, metadata):
        """
        /!\ id attribute has to be defined before calling this super method
        """
        self.xml_trees = {}

        self.metadata = {} if metadata is None else metadata
        self.metadata['Type'] = 'Crue10'
        self.metadata = add_default_missing_metadata(self.metadata, type(self).METADATA_FIELDS)

        if access == 'r':
            if files is None:
                raise RuntimeError
            if set(files.keys()) != set(type(self).FILES_XML + type(self).FILES_SHP):
                raise RuntimeError
            self.files = files
        elif access == 'w':
            self.files = {}
            if files is None:
                for xml_type in type(self).FILES_XML:
                    self.files[xml_type] = self.id[3:] + '.' + xml_type + '.xml'
            else:
                raise RuntimeError

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

    def _get_xml_root_and_set_comment(self, xml):
        root = ET.parse(self.files[xml]).getroot()

        # Sets comment if the tag is found
        comment_elt = root.find(PREFIX + 'Commentaire')
        if comment_elt is not None:
            self.comments[xml] = '' if comment_elt.text is None else comment_elt.text

        return root

    def _set_xml_trees(self):
        for xml_type in type(self).FILES_XML_WITHOUT_TEMPLATE:
            self.xml_trees[xml_type] = get_xml_root_from_file(self.files[xml_type])

    def _write_xml_file(self, xml, folder, **kwargs):
        template_render = JINJA_ENV.get_template(xml + '.xml').render(
            comment=self.comments[xml],
            **kwargs
        )

        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)
