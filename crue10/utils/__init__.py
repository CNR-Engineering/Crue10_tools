# coding: utf-8
from builtins import super  # Python2 fix
from datetime import datetime
from io import open  # Python2 fix
from jinja2 import Environment, FileSystemLoader
import logging
import os
import shutil
from lxml import etree

from crue10.utils.settings import XML_ENCODING


XML_DEFAULT_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'default')

XML_TEMPLATES_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'templates')

XSD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'xsd')

try:
    USERNAME = os.getlogin()
except AttributeError:
    try:
        USERNAME = os.environ['USERNAME']
    except:
        USERNAME = 'inconnu'

SELF_CLOSING_TAGS = [
    'IniCalcCI', 'IniCalcPrecedent', 'InterpolLineaire', 'Lois', 'OrdreDRSO',
    'HydrogrammeQapp', 'Limnigramme'  # dclm
]

PREFIX = "{http://www.fudaa.fr/xsd/crue}"


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def get_default_metadata():
    """Default metadata with updated dates"""
    date_now = datetime.now()
    current_date = date_now.strftime("%Y-%m-%dT%H:%M:%S.000")  # example: "2019-01-23T16:59:16.000"
    return {
        'IsActive': 'true',
        'Commentaire': '',
        'AuteurCreation': USERNAME,
        'DateCreation': current_date,
        'AuteurDerniereModif': USERNAME,
        'DateDerniereModif': current_date,
    }


def add_default_missing_metadata(metadata, fields):
    metadata_out = {}
    for field in fields:
        if field not in metadata:
            default_metadata = get_default_metadata()
            try:
                metadata_out[field] = default_metadata[field]
            except KeyError:
                logger.debug(metadata)
                raise CrueError("Le champ %s n'a pas de valeur par défaut, il faut le renseigner !" % field)
        else:
            metadata_out[field] = metadata[field]
    return metadata_out


def check_isinstance(obj, type):
    if obj is None:
        return
    if isinstance(type, list):
        has_error = True
        for subtype in type:
            if isinstance(obj, subtype):
                has_error = False
                break
        if has_error:
            raise CrueError("L'objet %s n'a pas un type correct (types attentus : %s)" %
                            (obj, [str(subtype) for subtype in type]))
    else:
        if not isinstance(obj, type):
            raise CrueError("L'objet %s n'est pas de type `%s`" % (obj, type))


def check_preffix(name, preffix):
    if not name.startswith(preffix):
        raise CrueError("Le nom `%s` ne commence pas par `%s`" % (name, preffix))


def float2str(value):
    """
    34.666664123535156 => not changed!
    1e30 => 1.0E30
    """
    text = str(value).replace('e+', 'E')
    if 'E' in text:
        # Exponent case
        if '.' not in text:
            text = text.replace('E', '.0E')
    return text
    # # Conventional rendering
    # text = format(value, '.15f')
    # return re.sub(r'\.([0-9])([0]+)$', r'.\1', text) # remove ending useless zeros


def write_default_xml_file(xml_type, file_path):
    shutil.copyfile(os.path.join(XML_DEFAULT_FOLDER, xml_type + '.xml'), file_path)


def get_xml_root_from_file(file_path):
    with open(file_path, 'r', encoding=XML_ENCODING) as in_xml:
        content = ''.join(in_xml.readlines())
        if not isinstance(content, str):  # Python2 fix on Linux
            content = content.encode(XML_ENCODING)
        return etree.fromstring(content)


def write_xml_from_tree(xml_tree, file_path):
    def avoid_self_closing_tags(elt):
        """Avoid some elements to be not self-closing"""
        if elt.tag.replace(PREFIX, '') not in SELF_CLOSING_TAGS:
            if elt.text is None:
                elt.text = ''
        for sub_elt in elt:
            avoid_self_closing_tags(sub_elt)
        return elt

    with open(file_path, 'w', encoding=XML_ENCODING) as out_xml:
        text = u'\ufeff'  # Add BOM for utf-8
        text += '<?xml version="1.0" encoding="UTF-8"?>\n'  # hardcoded xml declaration to control case and quotation marks
        text += etree.tostring(avoid_self_closing_tags(xml_tree), method='xml', encoding=XML_ENCODING,
                               pretty_print=False, xml_declaration=False).decode(XML_ENCODING)
        out_xml.write(text)


HTML_ESCAPE_TABLE = {
    "&": "&amp;",
    '"': "&quot;",
    "'": "&apos;",
    ">": "&gt;",
    "<": "&lt;",
}


def html_escape(text):
    """Produce entities within text."""
    return "".join(HTML_ESCAPE_TABLE.get(c, c) for c in text)


JINJA_ENV = Environment(loader=FileSystemLoader(XML_TEMPLATES_FOLDER))
JINJA_ENV.filters = {
    'float2str': float2str,
    'html_escape': html_escape
}


class CrueError(Exception):
    """!
    @brief Custom exception for Crue file content check
    """
    def __init__(self, message):
        """!
        @param message <str>: error message description
        """
        super().__init__(message)
        self.message = message


class CrueErrorGeometryNotFound(CrueError):
    def __init__(self, emh):
        super().__init__("%s n'a pas de géométrie !" % emh)
