# coding: utf-8
"""
Gestion des messages d'erreurs de Crue10.
Il s'agit de texte en français qui permet d'interprêter une erreur à partir de son identifiant et de ses paramètres
"""
import os.path
import xml.etree.ElementTree as ET

from crue10.utils import DATA_FOLDER_ABSPATH, ExceptionCrue10, logger, PREFIX


MSG_FILE = os.path.join(DATA_FOLDER_ABSPATH, 'fr_FR.msg.xml')


messages = {}
try:
    root = ET.parse(MSG_FILE).getroot()
    for elt in root.iter(PREFIX + 'Message'):
        text = elt[0].text
        if not isinstance(text, str):  # Python2 fix: encode for special characters
            text = text.encode('utf-8')
        messages[str(elt.get('ID'))] = text
except ET.ParseError as e:
    raise ExceptionCrue10("Erreur syntaxe XML dans `%s`:\n%s" % (MSG_FILE, e))


def parse_message(message_id, nom_emh, parametres):
    if message_id in messages:
        message = messages[message_id].replace('{nomEMH}', nom_emh)
        try:
            return message.format(*([''] + parametres))  # Add an empty string to count arguments from 1
        except IndexError:
            logger.warning("Le message `%s` (%s) n'a pas assez de valeurs : %s"
                           % (message_id, messages[message_id], parametres))
            return message
    logger.warning("Le message `%s` est inconnu" % message_id)
    if parametres:
        return 'parametres=' + ';'.join(parametres)
    return ''
