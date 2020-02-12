# coding: utf-8
import abc
from builtins import super  # python2 compatibility, requires module `future`
from collections import OrderedDict

from crue10.utils import check_isinstance


# ABC below is compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


QAPP, ZIMP, MANOEUVRE, BR_QRUIS, CA_QRUIS, ZIMPQ_TARAGE = 0, 1, 2, 3, 4, 5

# CLIM_TYPE_LABELS = {
#     QAPP: 'Qapp',
#     ZIMP: 'Zimp',
#     MANOEUVRE: 'Ouv',
#     BR_QRUIS: 'Qruis',
#     CA_QRUIS: 'Qruis',
#     ZIMPQ_TARAGE: '',  # FIXME
# }
#
# CLIM_TYPE_TAGS = {
#     QAPP: 'Qapp',
#     ZIMP: 'Zimp',
#     MANOEUVRE: 'Ouv',
#     BR_QRUIS: 'Qruis',
#     CA_QRUIS: 'Qruis',
#     ZIMPQ_TARAGE: '',  # FIXME
# }


class Calcul(ABC):
    """
    Abstract class for Sections
    """
    def __init__(self, nom, comment):
        self.id = nom
        self.comment = comment
        self.values = []  # (nom_emh, CLIM_TYPE_TO_TAG_VALUE.keys()[*], IsActive, value, sens)

    def ajouter_valeur(self, nom_emh, clim_tag, is_active, value, sens=None):
        check_isinstance(nom_emh, str)  # TODO: check that EMH exists
        check_isinstance(is_active, bool)
        check_isinstance(sens, [type(None), str])
        self.values.append((nom_emh, clim_tag, is_active, value, sens))


class CalcPseudoPerm(Calcul):
    CLIM_TYPE_TO_TAG_VALUE = {
        'CalcPseudoPermNoeudQapp': 'Qapp',
        'CalcPseudoPermNoeudNiveauContinuZimp': 'Zimp',
        'CalcPseudoPermBrancheOrificeManoeuvre': 'Ouv',
        'CalcPseudoPermBrancheSaintVenantQruis': 'Qruis',
        'CalcPseudoPermCasierProfilQruis': 'Qruis',
    }

    def ajouter_valeur(self, nom_emh, clim_tag, is_active, value, sens=None):
        check_isinstance(value, float)
        assert clim_tag in CalcPseudoPerm.CLIM_TYPE_TO_TAG_VALUE.keys()
        super().ajouter_valeur(nom_emh, clim_tag, is_active, value, sens)

    def get_Qapp_somme(self):
        sum = 0.0
        for _, clim_tag, _, value, _ in self.values:
            if clim_tag == QAPP:
                sum += value
        return sum

    def __repr__(self):
        return "Calcul pseudo-permanent #%s (%i valeur(s) aux noeuds)" % (self.id, len(self.values))


class CalcTrans(Calcul):
    CLIM_TYPE_TO_TAG_VALUE = {
        'CalcTransNoeudQapp': 'HydrogrammeQapp',
        'CalcTransNoeudNiveauContinuLimnigramme': 'Limnigramme',
        'CalcTransBrancheOrificeManoeuvre': 'Manoeuvre',
        'CalcTransHydrogrammeQruisBranche': 'HydrogrammeQruis',
        'CalcTransHydrogrammeQruisCasier': 'HydrogrammeQruis',
        'CalcTransNoeudNiveauContinuTarage': 'Tarage',
    }

    def ajouter_valeur(self, nom_emh, clim_tag, is_active, value, sens=None):
        check_isinstance(value, str)
        assert clim_tag in CalcTrans.CLIM_TYPE_TO_TAG_VALUE.keys()
        super().ajouter_valeur(nom_emh, clim_tag, is_active, value, sens)

    def __repr__(self):
        return "Calcul transitoire #%s" % self.id
