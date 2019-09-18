# coding: utf-8
"""
Classes for branches (or river reaches) in minor and major beds:
- Branche
    - 1 = BranchePdc
    - 2 = BrancheSeuilTransversal
    - 4 = BrancheSeuilLateral
    - 5 = BrancheOrifice
    - 6 = BrancheStrickler
    - 12 = BrancheNiveauxAssocies
    - 14 = BrancheBarrageGenerique
    - 15 = BrancheBarrageFilEau
    - 20 = BrancheSaintVenant
"""
import abc
from builtins import super  # python2 compatibility, requires module `future`
import numpy as np
from shapely.affinity import translate
from shapely.geometry import LineString, Point

from .noeud import Noeud
from .section import Section, SectionIdem, SectionInterpolee, SectionProfil, SectionSansGeometrie
from crue10.utils import check_isinstance, check_preffix, CrueError, logger


# ABC below is compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})

DIFF_XP_TO_WARN = 20.0  # m

DEFAULT_ELTS_SEUILS = np.array([(1.0, 0.0, 1.0)])

DEFAULT_ELTS_SEUILS_AVEC_PDC = np.array([(1.0, 0.0, 1.0, 1.0)])

DEFAULT_FORMULE_PDC = 'Borda'

DEFAULT_QLIMINF = -1.0E30  # m3/s

DEFAULT_QLIMSUP = 1.0E30  # m3/s


class Branche(ABC):
    """
    Abstract class for `Branche`
    - id <str>: branch identifier
    - type <int>: branch type (a key from `Branche.TYPES`)
    - is_active <bool>: True if the branch is active
    - geom <LineString>: polyline branch trace
    - noeud_amont <crue10.emh.noeud.Noeud>: upstream node
    - noeud_aval <crue10.emh.noeud.Noeud>: downstream node
    - sections <[crue10.emh.section.Section]>: list of sections
    - comment <str>: optional text explanation
    """

    TYPES = {
        1: 'BranchePdc',
        2: 'BrancheSeuilTransversal',
        4: 'BrancheSeuilLateral',
        5: 'BrancheOrifice',
        6: 'BrancheStrickler',
        12: 'BrancheNiveauxAssocies',
        14: 'BrancheBarrageGenerique',
        15: 'BrancheBarrageFilEau',
        20: 'BrancheSaintVenant'
    }

    # Branch types whose sections (at least 2) have a geometry (SectionProfil or SectionIdem)
    TYPES_WITH_GEOM = [2, 6, 15, 20]

    # Branch types which have a non-zero length value
    TYPES_WITH_LENGTH = [6, 20]

    # Branch types which should be located in the river bed (and not the floodplain)
    TYPES_IN_MINOR_BED = [1, 2, 20]

    def __init__(self, nom_branche, noeud_amont, noeud_aval, branch_type, is_active=True):
        check_preffix(nom_branche, 'Br_')
        check_isinstance(noeud_amont, Noeud)
        check_isinstance(noeud_aval, Noeud)
        if branch_type not in Branche.TYPES:
            raise RuntimeError
        self.id = nom_branche
        self.type = branch_type
        self.is_active = is_active
        if noeud_amont.geom is not None and noeud_aval.geom is not None:
            self.geom = LineString([(noeud_amont.geom.x, noeud_amont.geom.y), (noeud_aval.geom.x, noeud_aval.geom.y)])
        else:
            self.geom = None
        self.noeud_amont = noeud_amont
        self.noeud_aval = noeud_aval
        self.sections = []
        self.comment = ''

    @staticmethod
    def get_id_type_from_name(branch_type_name):
        for type_id, type_name in Branche.TYPES.items():
            if type_name == branch_type_name:
                return type_id
        return None

    @property
    def length(self):
        """Length displayed in FC (may differ from geometry)"""
        if self.type in Branche.TYPES_WITH_LENGTH:
            return self.sections[-1].xp
        else:
            return 0.0

    @property
    def type_name(self):
        return Branche.TYPES[self.type]

    def has_geom(self):
        return self.type in Branche.TYPES_WITH_GEOM

    def add_section(self, section, xp):
        check_isinstance(section, Section)
        if isinstance(section, SectionInterpolee):
            if self.type != 20:
                raise CrueError("La %s ne peut être affectée qu'à une branche Saint-Venant" % section)
        elif self.type in Branche.TYPES_WITH_GEOM:
            if not isinstance(section, SectionProfil) and not isinstance(section, SectionIdem):
                raise CrueError("La %s ne peut porter que des SectionProfil ou SectionIdem" % self)
        else:
            if not isinstance(section, SectionSansGeometrie):
                raise CrueError("La %s ne peut porter que des SectionSansGeometrie" % self)
        section.xp = xp
        self.sections.append(section)

    def set_geom(self, geom):
        check_isinstance(geom, LineString)
        self.geom = geom

    def shift_sectionprofil_to_extremity(self):
        """
        Shift first and last SectionProfil to branch extremity
        (a constant biais is introduced by Fudaa-Crue for the graphical representation)
        """
        for pos in (0, -1):
            section = self.sections[pos]
            if isinstance(section, SectionProfil):
                if pos == 0:
                    node = self.noeud_amont.geom
                else:
                    node = self.noeud_aval.geom
                section_point = section.geom_trace.intersection(self.geom)
                if isinstance(section_point, Point):
                    dx = node.x - section_point.x
                    dy = node.y - section_point.y
                    self.sections[pos].set_trace(
                        translate(section.geom_trace, xoff=dx, yoff=dy))

    def normalize_sections_xp(self):
        """
        Recompute section xp to correspond to geometric distance (original values are taken from drso).
        Last section xp will correspond exactly to the branch length.
        """
        xp_max = self.sections[-1].xp
        length = self.geom.length
        if self.type in Branche.TYPES_WITH_LENGTH and abs(xp_max - length) > DIFF_XP_TO_WARN:
            logger.warn("La longueur de la branche `%s` est estimée à %.2fm (non pas %.2fm)."
                        % (self.id, length, xp_max))
        for i, section in enumerate(self.sections):
            try:
                section.xp = section.xp * length / xp_max
            except ZeroDivisionError:
                section.xp = (i / (len(self.sections) - 1)) * length

    def __repr__(self):
        return "Branche [%i] #%s: %s -> %s (%i sections)" % (self.type, self.id,
                                                             self.noeud_amont, self.noeud_aval, len(self.sections))


class BranchePdC(Branche):
    """
    BrancheSaintVenant - #1
    - loi_QPdc
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 1, is_active)
        self.loi_QPdc = np.array([(-15000.0, 0.0)])

    @property
    def name_loi_LoiQPdc(self):
        return 'LoiQPdc_%s' % self.id[3:]


class BrancheSeuilTransversal(Branche):
    """
    BrancheSeuilTransversal - #2
    - formule_pdc <str>: 'Borda' or 'Divergent'
    - elts_seuil <2D-array>: ndarray(dtype=float, ndim=2 with 4 columns)
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 2, is_active)
        self.formule_pdc = DEFAULT_FORMULE_PDC
        self.elts_seuil = DEFAULT_ELTS_SEUILS_AVEC_PDC


class BrancheSeuilLateral(Branche):
    """
    BrancheSeuilLateral - #4
    - formule_pdc <str>: 'Borda' or 'Divergent'
    - elts_seuil <2D-array>: ndarray(dtype=float, ndim=2 with 4 columns)
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 4, is_active)
        self.formule_pdc = DEFAULT_FORMULE_PDC
        self.elts_seuil = DEFAULT_ELTS_SEUILS_AVEC_PDC


class BrancheOrifice(Branche):
    """
    BrancheOrifice - #5
    - CoefCtrLim <float>: "Coefficient maximum de contraction de la veine submergée"
    - Largeur <float>: "Largeur"
    - Zseuil <float>: "Cote du radier du clapet"
    - CoefD <float>: ?
    - Haut <float>: "Hauteur du clapet à pleine ouverture"
    - SensOrifice <str>: "Sens de l'écoulement"
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 5, is_active)
        self.CoefCtrLim = 0.65
        self.Largeur = 1.0
        self.Zseuil = 0.0
        self.Haut = 1.0
        self.CoefD = 1.0
        self.SensOrifice = 'Bidirect'


class BrancheStrickler(Branche):
    """
    BrancheStrickler - #6
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 6, is_active)


class BrancheNiveauxAssocies(Branche):
    """
    BrancheNiveauxAssocies - #12
    - QLimInf: "Débit  minimum admis dans la branche"
    - QLimSup: "Débit maximum admis dans la branche"
    - loi_ZavZam <2D-array>: ndarray(dtype=float, ndim=2 with 2 columns)
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 12, is_active)
        self.QLimInf = DEFAULT_QLIMINF
        self.QLimSup = DEFAULT_QLIMSUP
        self.loi_ZavZam = np.array([(-15.0, -15.0)])

    @property
    def name_loi_ZavZam(self):
        return 'LoiZavZam_%s' % self.id[3:]


class BrancheBarrageGenerique(Branche):
    """
    BrancheBarrageGenerique - #14
    - section_pilotage <crue10.emh.section.Section>: section de pilotage
    - QLimInf: "Débit  minimum admis dans la branche"
    - QLimSup: "Débit maximum admis dans la branche"
    - loi_QDz <2D-array>: ndarray(dtype=float, ndim=2 with 2 columns)
    - loi_QpilZam <2D-array>: ndarray(dtype=float, ndim=2 with 2 columns)
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 14, is_active)
        self.section_pilotage = None
        self.QLimInf = DEFAULT_QLIMINF
        self.QLimSup = DEFAULT_QLIMSUP
        self.loi_QDz = np.array([(-15000.0, -1.0E30)])
        self.loi_QpilZam = np.array([(0.0, -15.0)])

    @property
    def name_loi_QDz(self):
        return 'LoiQDz_%s' % self.id[3:]

    @property
    def name_loi_QpilZam(self):
        return 'LoiQpilZam_%s' % self.id[3:]


class BrancheBarrageFilEau(Branche):
    """
    BrancheBarrageFilEau - #15
    - section_pilotage <crue10.emh.section.Section>: section de pilotage
    - QLimInf: "Débit  minimum admis dans la branche"
    - QLimSup: "Débit maximum admis dans la branche"
    - loi_QZam <2D-array>: ndarray(dtype=float, ndim=2 with 2 columns)
    - elts_seuil <2D-array>: ndarray(dtype=float, ndim=2 with 3 columns)
    """
    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 15, is_active)
        self.section_pilotage = None
        self.QLimInf = DEFAULT_QLIMINF
        self.QLimSup = DEFAULT_QLIMSUP
        self.loi_QZam = np.array([(0.0, -15.0)])
        self.elts_seuil = DEFAULT_ELTS_SEUILS

    @property
    def name_loi_QZam(self):
        return 'LoiQpilZam_%s' % self.id[3:]


class BrancheSaintVenant(Branche):
    """
    BrancheSaintVenant - #20
    - CoefSinuo <float>: "coefficient de sinuosité de la branche, rapport des longueurs des axes hydrauliques
         du lit mineur et du lit majeur"
    - CoefBeta <float>: "coefficient de modulation global à la branche du coefficient de Boussinesq,
         afin de tenir compte de la forme du profil des vitesses sur le calcul de la QdM de l'écoulement"
    - CoefRuis <float>: "coefficient modulation du débit linéique de ruissellement"
    - CoefRuisQdm <float>: "coefficient de prise en compte du débit de ruissellement dans la QdM de l'écoulement"
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 20, is_active)
        self.CoefSinuo = 1.0
        self.CoefBeta = 1.0
        self.CoefRuis = 0.0
        self.CoefRuisQdm = 0.0


BRANCHE_CLASSES = [BranchePdC, BrancheSeuilTransversal, BrancheSeuilLateral, BrancheOrifice, BrancheStrickler,
                   BrancheNiveauxAssocies, BrancheBarrageGenerique, BrancheBarrageFilEau, BrancheSaintVenant]
