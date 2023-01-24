# coding: utf-8
from crue10.utils import PREFIX
from crue10.utils import ExceptionCrue10


BOOLEAN_TAGS = ['SortieEcran', 'SortieFichier']
SEVERITE_TAGS = ['VerbositeEcran', 'VerbositeFichier']
TYPE_SEVERITE = ['DEBUG3', 'DEBUG2', 'DEBUG1', 'FCT3', 'FCT2', 'FCT1', 'INFO', 'WARN', 'ERRNBLK', 'ERRBLK', 'FATAL']


def elt_to_dict(elt):
    res = {}
    for sub_elt in elt:
        tag_name = sub_elt.tag[len(PREFIX):]
        if tag_name in BOOLEAN_TAGS:
            res[tag_name] = sub_elt.text == 'true'
        else:
            if tag_name in SEVERITE_TAGS:
                if sub_elt.text not in TYPE_SEVERITE:
                    raise ExceptionCrue10("La verbosité `%s` n'est pas standard" % sub_elt.text)
            res[tag_name] = sub_elt.text
    return res


class Sorties:
    """
    Sortie: paramétrage des traces et fichier de sortie des pré-traitements et du calcul

    :ivar avancement: avancement
    :vartype avancement: dict
    :ivar trace: trace
    :vartype trace: dict
    :ivar resultat: résultat
    :vartype resultat: dict
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

    def __repr__(self):
        return "Sortie: avancement ({}), trace ({}), résultat ({})".format(self.avancement, self.trace, self.resultat)
