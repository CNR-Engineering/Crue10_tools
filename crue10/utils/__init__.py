# coding: utf-8
from builtins import super  # Python2 fix
from datetime import datetime
from io import open  # Python2 fix
from jinja2 import Environment, FileSystemLoader
from jinja2.filters import do_lower
import logging
import numpy as np
import os
import re
import shutil
from lxml import etree

from crue10.utils.filters import float2str, html_escape
from crue10.utils.settings import XML_ENCODING


DATA_FOLDER_ABSPATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data')

try:
    USERNAME = os.getlogin()
except:
    try:
        USERNAME = os.environ['USERNAME']
    except:
        USERNAME = 'inconnu'

SELF_CLOSING_TAGS = [
    'IniCalcCI', 'IniCalcPrecedent', 'InterpolLineaire', 'Lois', 'OrdreDRSO',
    'InterpolBaignoire',  # opti
    'HydrogrammeQapp', 'Limnigramme',  # dclm
    'Qmode', 'DefQregul', 'DefZregul', 'Qabs', 'Zabs', 'CondMode',  #dreg
]

PREFIX = "{http://www.fudaa.fr/xsd/crue}"

XSI_SCHEMA_LOCATION = '{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'

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
                raise ExceptionCrue10("Le champ %s n'a pas de valeur par défaut, il faut le renseigner !" % field)
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
            raise ExceptionCrue10("L'objet %s n'a pas un type correct (types attentus : %s)" %
                                  (obj, [str(subtype) for subtype in type]))
    else:
        if not isinstance(obj, type):
            raise ExceptionCrue10("L'objet %s n'est pas de type `%s`" % (obj, type))


def check_2d_array_shape(array, min_axis_0, len_axis_1):
    len_axis_0, len_axis_1 = array.shape
    if len_axis_0 < min_axis_0:
        raise ExceptionCrue10("Le premier axe n'a pas au moins %i valeurs" % min_axis_0)
    if len_axis_1 != len_axis_1:
        raise ExceptionCrue10("Le second axe n'a pas exactement %i valeurs" % len_axis_1)


def check_strictly_increasing(array, label):
    if any(x > y for x, y in zip(array, array[1:])):
        raise ExceptionCrue10("Les valeurs de %s ne sont pas strictement croissantes %s" % (label, array))


def check_preffix(name, preffix):
    """
    Lève une exception si le nom de l'élément ne commence par le préffixe

    :param name: nom de l'élément
    :param preffix: préffixe à vérifier
    """
    if not name.startswith(preffix):
        raise ExceptionCrue10("Le nom `%s` ne commence pas par `%s`" % (name, preffix))


def get_optional_commentaire(elt):
    """Returns text of Commentaire element if found, empty string else"""
    sub_elt = elt.find(PREFIX + 'Commentaire')
    if sub_elt is not None:
        if sub_elt.text is not None:
            return sub_elt.text
    return ''


def parse_loi(elt, group='EvolutionFF', line='PointFF'):
    elt_group = elt.find(PREFIX + group)
    values = []
    for point_ff in elt_group.findall(PREFIX + line):
        values.append([float(v) for v in point_ff.text.split()])
    return np.array(values)


def write_default_xml_file(xml_type, version_grammaire, file_path):
    shutil.copyfile(os.path.join(DATA_FOLDER_ABSPATH, version_grammaire, 'fichiers_vierges',
                                 'default.%s.xml' % xml_type), file_path)


def get_xml_root_from_file(file_path):
    with open(file_path, 'r', encoding=XML_ENCODING) as in_xml:
        content = ''.join(in_xml.readlines())
        if not isinstance(content, str):  # Python2 fix on Linux
            content = content.encode(XML_ENCODING)
        return etree.fromstring(content)


def write_xml_from_tree(xml_tree, file_path):
    # Avoid some self-closing tags
    def avoid_self_closing_tags(elt):
        """Avoid some elements to be not self-closing"""
        if not isinstance(elt, etree._Comment):  # ignore comments
            if elt.tag.replace(PREFIX, '') not in SELF_CLOSING_TAGS:
                if elt.text is None:
                    elt.text = ''
            for sub_elt in elt:
                avoid_self_closing_tags(sub_elt)
        return elt

    xml_tree = avoid_self_closing_tags(xml_tree)

    # Convert xml tree to string
    main_text = etree.tostring(xml_tree, method='xml', encoding=XML_ENCODING,
                               pretty_print=False, xml_declaration=False).decode(XML_ENCODING)

    # Insert HTML entities in <Commentaire> tags
    def insert_html_entities(match):
        text = html_escape(match.group(1))
        return "<Commentaire>%s</Commentaire>" % text

    main_text = re.sub(r'<Commentaire>(.*?)</Commentaire>', insert_html_entities, main_text, flags=re.S)

    # Write XML file
    with open(file_path, 'w', encoding=XML_ENCODING) as out_xml:
        text = u'\ufeff'  # Add BOM for utf-8
        text += '<?xml version="1.0" encoding="UTF-8"?>\n'  # hardcoded xml declaration to control case and quotation marks
        text += main_text
        out_xml.write(text)


JINJA_ENV = Environment(loader=FileSystemLoader(os.path.join(DATA_FOLDER_ABSPATH)))
JINJA_ENV.filters = {
    'abs': abs,
    'float2str': float2str,
    'html_escape': html_escape,
    'lower': do_lower,
}


class ExceptionCrue10(Exception):
    """Exception Crue10 générale"""

    def __init__(self, message):
        """
        :param message: messsage décrivant l'erreur
        :type message: str
        """
        super().__init__(message)
        self.message = message


class ExceptionCrue10GeometryNotFound(ExceptionCrue10):
    """Exception Crue10 pour les problèmes de géométrie (fichiers SHP en particulier)"""

    def __init__(self, emh):
        super().__init__("%s n'a pas de géométrie !" % emh)


class ExceptionCrue10Grammar(ExceptionCrue10):
    """Exception Crue10 pour les problèmes de grammaire"""

    def __init__(self, message):
        """
        :param message: messsage décrivant l'erreur
        :type message: str
        """
        super().__init__(message)
        self.message = message


def duration_seconds_to_iso8601(duration_in_seconds):
    """
    Converts a duration in seconds to ISO 8601 text format
    (See ISO format at https://fr.wikipedia.org/wiki/ISO_8601#Dur%C3%A9e)

    :param duration_in_seconds: float measuring a duration in seconds
    :type duration_in_seconds: float
    :return: ISO 8601 text format (e.g. "P0Y0M0DT0H0M0S". Info: the letter `T` separates days and hours)
    """
    if duration_in_seconds < 0:
        raise ExceptionCrue10("Une durée négative n'est pas possible!")
    txt = 'P0Y0M'

    # Number of days
    nb_days = duration_in_seconds // (24 * 3600)
    txt += '%iDT' % nb_days
    duration_in_seconds = duration_in_seconds - nb_days * 24 * 3600

    # Number of hours
    nb_hours = duration_in_seconds // 3600
    txt += '%iH' % nb_hours
    duration_in_seconds = duration_in_seconds - nb_hours * 3600

    # Number of minutes
    nb_minutes = duration_in_seconds // 60
    txt += '%iM' % nb_minutes
    duration_in_seconds = duration_in_seconds - nb_minutes * 60

    # Number of seconds
    if duration_in_seconds == 0.0:
        txt += '0S'
    elif duration_in_seconds == int(duration_in_seconds):
        txt += '%.0fS' % duration_in_seconds
    else:
        txt += '%.2fS' % duration_in_seconds  # truncation after 2 digits

    return txt


def duration_iso8601_to_seconds(duration_in_iso8601):
    """
    Converts ISO 8601 text format to a duration in seconds

    :param duration_in_iso8601: ISO 8601 text format (e.g. "P0Y0M0DT0H0M0S". Info: the letter `T` separates days and hours)
    :type duration_in_iso8601: str
    :return: float measuring a duration in seconds
    """
    match = re.match(r"^P0Y0M(?P<days>[\d.]+)DT(?P<hours>[\d.]+)H(?P<minutes>[\d.]+)M(?P<seconds>[\d.]+)S$",
                     duration_in_iso8601)
    return (float(match.group('seconds')) +
            60 * (float(match.group('minutes')) +
                  60 * (float(match.group('hours')) +
                        24 * float(match.group('days')))))


def extract_pdt_from_elt(elt):
    """
    Extraction du pas de temps (constant ou variable) à partir de l'élément XML

    :param elt: XML tree
    :return: flottant (si pas de temps constant) ou une liste de tuple (si variable)

    # Exemple d'un pas de temps constant

    .. code-block:: xml

       <PdtRes>
         <PdtCst>P0Y0M0DT1H0M0S</PdtCst>
       </PdtRes>

    # Exemple d'un pas de temps variable (en permanent)

    .. code-block:: xml

       <Pdt>
         <PdtVar>
           <ElemPdt>
             <NbrPdt>10</NbrPdt>
             <DureePdt>P0Y0M0DT0H12M0S</DureePdt>
           </ElemPdt>
           <ElemPdt>
             <NbrPdt>100</NbrPdt>
             <DureePdt>P0Y0M0DT3H0M0S</DureePdt>
           </ElemPdt>
         </PdtVar>
       </Pdt>

    """
    assert len(elt) == 1
    if elt[0].tag.endswith('PdtCst'):
        return duration_iso8601_to_seconds(elt[0].text)
    elif elt[0].tag.endswith('PdtVar'):
        res = []
        for elem in elt[0]:
            res.append((int(elem.find(PREFIX + 'NbrPdt').text),
                        duration_iso8601_to_seconds(elem.find(PREFIX + 'DureePdt'))))
        return res
    else:
        raise NotImplementedError("Pas de temps impossible à traiter")


def check_xml_content(xml_content, xsd_schema):
    errors_list = []
    try:
        xml_tree = etree.fromstring(xml_content)
        try:
            xsd_schema.assertValid(xml_tree)
        except etree.DocumentInvalid:
            for error in xsd_schema.error_log:
                error_str = "Invalid XML at line %i: %s" % (error.line, error.message)
                if not isinstance(error_str, str):  # Python2 fix: encode
                    error_str = error_str.encode('utf-8')
                errors_list.append(error_str)
    except etree.XMLSyntaxError as e:
        error_str = "Error XML: %s" % e
        if not isinstance(error_str, str):  # Python2 fix: encode
            error_str = error_str.encode('utf-8')
        errors_list.append(error_str)
    return errors_list


def check_xml_file(xml_path, version_grammaire):
    logger.debug("Validation XSD (grammaire %s) de %s" % (version_grammaire, xml_path))
    file_splitted = xml_path.split('.')
    xml_type = file_splitted[-2]
    xsd_path = os.path.join(DATA_FOLDER_ABSPATH, version_grammaire, 'xsd',
                            '%s-%s.xsd' % (xml_type, version_grammaire))
    xsd_tree = etree.parse(xsd_path)
    xsd_tree.xinclude()  # replace `xs:include` by its content

    with open(xml_path, 'r', encoding=XML_ENCODING) as in_xml:
        content = '\n'.join(in_xml.readlines())
        xsd_schema = etree.XMLSchema(xsd_tree)
        return check_xml_content(content, xsd_schema)
