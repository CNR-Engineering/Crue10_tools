# coding: utf-8
from crue10.utils import PREFIX


BOOLEAN_TAGS = ['SortieEcran', 'SortieFichier']


def elt_to_dict(elt):
    res = {}
    for sub_elt in elt:
        tag_name = sub_elt.tag[len(PREFIX):]
        if tag_name in BOOLEAN_TAGS:
            res[tag_name] = sub_elt.text == 'true'
        else:
            res[tag_name] = sub_elt.text
    return res


class Sorties:
    """
    Sortie: paramétrage des traces et fichiers de sortie
    """

    def __init__(self):
        self.avancement = {
            'SortieFichier': True,
        }
        self.trace = {
            'SortieEcran': True,
            'SortieFichier': True,
            'VerbositeEcran': 'INFO',
            'VerbositeFichier': 'INFO',
        }
        self.resultat = {
            'SortieFichier': True,
        }

    def set_avancement(self, elt):
        self.avancement = elt_to_dict(elt)

    def set_trace(self, elt):
        self.trace = elt_to_dict(elt)

    def set_resultat(self, elt):
        self.resultat = elt_to_dict(elt)
