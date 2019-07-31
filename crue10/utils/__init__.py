from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import logging
import os


XML_ENCODING = 'utf-8'

XML_DEFAULT_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'default')

XML_TEMPLATES_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'templates')

XSD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'xsd')

CURRENT_DATE = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000")  # example: 2019-01-23T16:59:16.000

USERNAME = os.getlogin()

DEFAULT_METADATA = {
    'IsActive': 'true',
    'Commentaire': '',
    'AuteurCreation': USERNAME,
    'DateCreation': CURRENT_DATE,
    'AuteurDerniereModif': USERNAME,
    'DateDerniereModif': CURRENT_DATE,
}

PREFIX = "{http://www.fudaa.fr/xsd/crue}"


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


def add_default_missing_metadata(metadata, fields):
    metadata_out = {}
    for field in fields:
        if field not in metadata:
            try:
                metadata_out[field] = DEFAULT_METADATA[field]
            except KeyError:
                logger.debug(metadata)
                raise CrueError("Le champ %s n'a pas de valeur par défaut, il faut le renseigner !" % field)
        else:
            metadata_out[field] = metadata[field]
    return metadata_out


def check_isinstance(obj, type):
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
    return str(value).replace('e+', 'E').replace('.0E', 'E')


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
