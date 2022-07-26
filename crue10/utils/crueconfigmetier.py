import os.path
import xml.etree.ElementTree as ET

from crue10.utils import DATA_FOLDER_ABSPATH, ExceptionCrue10, PREFIX


#: Chemin vers le fichier CCM
CCM_FILE = os.path.join(DATA_FOLDER_ABSPATH, 'CrueConfigMetier.xml')


ENUM_SEVERITE = {}
try:
    root = ET.parse(CCM_FILE).getroot()
    for elt in root.find(PREFIX + 'TypeEnums').find(PREFIX + "ItemTypeEnum[@Nom='Ten_Severite']"):
        ENUM_SEVERITE[elt.text] = int(elt.attrib['Id'])
except ET.ParseError as e:
    raise ExceptionCrue10("Erreur syntaxe XML dans `%s`:\n%s" % (CCM_FILE, e))
