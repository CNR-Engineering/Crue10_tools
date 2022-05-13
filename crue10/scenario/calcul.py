# coding: utf-8
import abc
from builtins import super  # python2 compatibility, requires module `future`
from collections import OrderedDict

from crue10.utils import check_isinstance


# ABC below is compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


class Calcul(ABC):
    """
    Abstract class for Sections

    - id
    - comment
    - values:
        * nom_emh
        * CLIM_TYPE_TO_TAG_VALUE.keys()[*]
        * IsActive <bool>
        * value: en permanent valeur flottante, en transitoire nom de la loi
        * sens: sens ouverture (None si non concerné)
        * type loi
        * param loi
        * nom_fic
    """
    def __init__(self, nom, comment=''):
        self.id = nom
        self.comment = comment
        self.values = []

    def ajouter_valeur(self, nom_emh, clim_tag, is_active, value, sens=None, typ_loi=None, param_loi=None, nom_fic=None):
        check_isinstance(nom_emh, str)  # TODO: check that EMH exists
        check_isinstance(is_active, bool)
        check_isinstance(sens, [type(None), str])
        self.values.append([nom_emh, clim_tag, is_active, value, sens, typ_loi, param_loi, nom_fic])


class CalcPseudoPerm(Calcul):
    CLIM_TYPE_TO_TAG_VALUE = {
        'CalcPseudoPermNoeudQapp': 'Qapp',
        'CalcPseudoPermNoeudNiveauContinuZimp': 'Zimp',
        'CalcPseudoPermBrancheOrificeManoeuvre': 'Ouv',
        'CalcPseudoPermBrancheSaintVenantQruis': 'Qruis',
        'CalcPseudoPermCasierProfilQruis': 'Qruis',
    }

    def ajouter_valeur(self, nom_emh, clim_tag, is_active, value, sens=None, typ_loi=None, param_loi=None, nom_fic=None):
        check_isinstance(value, float)
        assert clim_tag in CalcPseudoPerm.CLIM_TYPE_TO_TAG_VALUE.keys()
        super().ajouter_valeur(nom_emh, clim_tag, is_active, value, sens, typ_loi, param_loi, nom_fic)

    def get_valeur(self, nom_emh):
        idx = [emh_id for emh_id, _, _, _, _, _, _, _ in self.values].index(nom_emh)
        nom_emh, clim_tag, is_active, value, sens, typ_loi, param_loi, nom_fic = self.values[idx]
        return value

    def multiplier_valeur(self, nom_emh, facteur):
        check_isinstance(facteur, float)
        idx = [emh_id for emh_id, _, _, _, _, _, _, _ in self.values].index(nom_emh)
        nom_emh, clim_tag, is_active, value, sens, typ_loi, param_loi, nom_fic = self.values[idx]
        self.values[idx] = nom_emh, clim_tag, is_active, value * facteur, sens, typ_loi, param_loi, nom_fic

    def set_valeur(self, nom_emh, value):
        check_isinstance(value, float)
        idx = [emh_id for emh_id, _, _, _, _, _, _, _ in self.values].index(nom_emh)
        nom_emh, clim_tag, is_active, _, sens, typ_loi, param_loi, nom_fic = self.values[idx]
        self.values[idx] = nom_emh, clim_tag, is_active, value, sens, typ_loi, param_loi, nom_fic

    def get_somme_Qapp(self):
        sum = 0.0
        for _, clim_tag, _, value, _, _, _, _ in self.values:
            if clim_tag == 'CalcPseudoPermNoeudQapp':
                sum += value
        return sum

    def get_somme_positive_Qapp(self):
        sum = 0.0
        for _, clim_tag, _, value, _, _, _, _ in self.values:
            if clim_tag == 'CalcPseudoPermNoeudQapp' and value > 0:
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
        'CalcTransBrancheSaintVenantQruis': 'HydrogrammeQruis',
    }

    # MEC-Crue10: Ajout de CLimM spéciales (n'ayant pas la forme des autres): enchaînement, régulation
    CLIM_TYPE_SPECIAL_VALUE = {
        'CalcTransBrancheOrificeManoeuvreRegul': 'ManoeuvreRegul',
        'CalcTransNoeudQapp': 'HydrogrammeQappExt',
        'CalcTransNoeudUsi': '',
        'CalcTransNoeudBg1': '',
        'CalcTransNoeudBg2': '',
        'CalcTransNoeudBg1Av': '',
        'CalcTransNoeudBg2Av': '',
    }

    def ajouter_valeur(self, nom_emh, clim_tag, is_active, value, sens=None, typ_loi=None, param_loi=None, nom_fic=None):
        check_isinstance(value, str)
        assert clim_tag in CalcTrans.CLIM_TYPE_TO_TAG_VALUE or clim_tag in CalcTrans.CLIM_TYPE_SPECIAL_VALUE
        super().ajouter_valeur(nom_emh, clim_tag, is_active, value, sens, typ_loi, param_loi, nom_fic)

    def __repr__(self):
        return "Calcul transitoire #%s" % self.id
