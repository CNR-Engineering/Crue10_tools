# coding: utf-8
"""
Classes for cross-section in minor and major beds:
- FrictionLaw
- LitNumerote
- LimiteGeom
- Section
    - SectionProfil
    - SectionIdem
    - SectionInterpolee
    - SectionSansGeometrie
"""
import abc
from builtins import super  # python2 compatibility, requires module `future`
from copy import deepcopy
import numpy as np
from shapely.geometry import LineString

from crue10.utils import check_isinstance, check_preffix, CrueError, logger


# ABC below is compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})

DIFF_XP = 0.1  # m

DISTANCE_TOL = 0.01  # m


class FrictionLaw:
    """
    Friction law (Strickler coefficient could vary with Z elevation)
    - id <str>: friction law identifier
    - type <str>: friction law type
    - loi_Fk <2D-array>: ndarray(dtype=float, ndim=2) with Stricker coefficient varying with elevation
    """

    TYPES = ['FkSto', 'Fk']

    def __init__(self, nom_loi_frottement, type, loi_Fk):
        check_preffix(nom_loi_frottement, 'Fk')
        check_isinstance(loi_Fk, np.ndarray)
        if type not in FrictionLaw.TYPES:
            raise RuntimeError
        self.id = nom_loi_frottement
        self.type = type
        self.loi_Fk = loi_Fk


DEFAULT_FK_STO = FrictionLaw('FkSto_K0_0001', 'FkSto', np.array([(0.0, 0.0)]))
DEFAULT_FK_MAX = FrictionLaw('Fk_DefautMaj', 'Fk', np.array([(-15.0, 8.0)]))
DEFAULT_FK_MIN = FrictionLaw('Fk_DefautMin', 'Fk', np.array([(-15.0, 8.0)]))


class LitNumerote:
    """
    Lit numéroté (= intervalle entre 2 limites de lit)
    - id <str>: bed identifier (a key of `BED_NAMES`)
    - xt_min <str>: first curvilinear abscissa
    - xt_max <str>: first curvilinear abscissa
    - friction_law <FrictionLaw>: friction law (take the associated default law if it is not given)
    """

    BED_NAMES = ['Lt_StoD', 'Lt_MajD', 'Lt_Mineur', 'Lt_MajG', 'Lt_StoG']
    LIMIT_NAMES = ['RD', 'StoD-MajD', 'MajD-Min', 'Min-MajG', 'MajG-StoG', 'RG']

    def __init__(self, nom_lit, xt_min, xt_max, friction_law=None):
        if nom_lit not in LitNumerote.BED_NAMES:
            raise RuntimeError
        self.id = nom_lit
        self.xt_min = xt_min
        self.xt_max = xt_max
        if friction_law is None:
            if 'Sto' in nom_lit:
                friction_law = DEFAULT_FK_STO
            elif 'Maj' in nom_lit:
                friction_law = DEFAULT_FK_MAX
            else:
                friction_law = DEFAULT_FK_MIN
        self.friction_law = friction_law

    @property
    def is_active(self):
        return 'Maj' in self.id or 'Min' in self.id

    @property
    def is_mineur(self):
        return 'Min' in self.id

    def __repr__(self):
        return 'LitNumeroté #%s (%f -> %s)' % (self.id, self.xt_min, self.xt_max)


class LimiteGeom:
    """
    Geometric limit
    - id <str>: bed identifier
    - xt <str>: curvilinear abscissa
    """
    def __init__(self, id, xt):
        check_preffix(id, 'Et_')
        self.id = id
        self.xt = xt

    def __repr__(self):
        return 'Limite #%s (%f)' % (self.id, self.xt)


class Section(ABC):
    """
    Abstract class for Sections
    - id <str>: section identifier
    - xp <float>: curvilinear abscissa of section on its associated branch
    - is_active <bool>: True if the section is active (it is associated to an active branch)
    - CoefPond <float>: "coefficient de pondération amont/aval de la discrétisation de la perte de charge régulière J
        entre la section et sa suivante"
    - CoefConv <float>: "coefficient de perte de charge ponctuelle en cas de convergence entre la section et sa
        suivante"
    - CoefDiv <float>: "coefficient de perte de charge ponctuelle en cas de divergence entre la section et sa suivante"
    - comment <str>: optional text explanation
    """

    def __init__(self, nom_section):
        self.id = nom_section
        self.is_active = False
        self.xp = -1
        self.CoefPond = 0.5
        self.CoefConv = 0.0
        self.CoefDiv = 0.0
        self.comment = ''

    def __repr__(self):
        return '%s #%s' % (self.__class__.__name__, self.id)


class SectionProfil(Section):
    """
    SectionProfil
    - nom_profilsection <str>: profil section identifier (should start with `Ps_`)
    - xt_axe <float>: transversal position of hydraulic axis
    - xz <2D-array>: ndarray(dtype=float, ndim=2)
        Array containing series of transversal abscissa and elevation (first axis should be strictly increasing)
    - geom_trace <LineString>: polyline section trace (/!\ only between left and right bank)
    - lits_numerotes <[LitNumerote]>: lits numérotés
    - limites_geom <[LimiteGeom]>: limites géométriques (thalweg, axe hydraulique...)
    """

    def __init__(self, nom_section, nom_profilsection=None):
        super().__init__(nom_section)
        self.nom_profilsection = ''
        self.set_profilsection_name(nom_profilsection)
        self.xz = None
        self.geom_trace = None
        self.fente = None
        self.lits_numerotes = []
        self.limites_geom = []

    def set_profilsection_name(self, nom_profilsection=None):
        if nom_profilsection is None:
            self.nom_profilsection = 'Ps_' + self.id[3:]
        else:
            check_preffix(nom_profilsection, 'Ps_')
            self.nom_profilsection = nom_profilsection

    @property
    def xt_axe(self):
        """Curvilinear abscissa of hydraulic axis intersection"""
        for limite in self.limites_geom:
            if limite.id == 'Et_AxeHyd':
                return limite.xt
        raise CrueError("Limite 'Et_AxeHyd' could not be found for %s" % self)

    @property
    def has_fente(self):
        return self.fente is not None

    @property
    def xz_filtered(self):
        return self.xz[np.logical_and(self.lits_numerotes[0].xt_min <= self.xz[:, 0],
                                      self.xz[:, 0] <= self.lits_numerotes[-1].xt_max), :]

    def set_xz(self, array):
        check_isinstance(array, np.ndarray)
        self.xz = array

    def set_trace(self, trace):
        check_isinstance(trace, LineString)
        if trace.has_z:
            raise CrueError("La trace de la %s ne doit pas avoir de Z !" % self)
        if not self.lits_numerotes:
            raise CrueError('xz has to be set before (to check consistency)')
        self.geom_trace = trace

        # Display a warning if geometry is not consistent with self.xz array
        range_xt = self.xz_filtered[:, 0].max() - self.xz_filtered[:, 0].min()
        diff_xt = range_xt - self.geom_trace.length
        if abs(diff_xt) > 1e-2:
            logger.warn("Écart de longueur pour la section %s: %s" % (self, diff_xt))

    def set_fente(self, largeur, profondeur):
        self.fente = (largeur, profondeur)

    def set_lits_numerotes(self, xt_list):
        """Add directly the 5 beds from a list of 6 ordered xt values"""
        if len(xt_list) != 6:
            raise RuntimeError
        if any(x > y for x, y in zip(xt_list, xt_list[1:])):
            raise CrueError("Les valeurs de xt ne sont pas croissantes")
        for bed_name, xt_min, xt_max in zip(LitNumerote.BED_NAMES, xt_list, xt_list[1:]):
            lit_numerote = LitNumerote(bed_name, xt_min, xt_max)
            self.lits_numerotes.append(lit_numerote)

    def add_lit_numerote(self, lit_numerote):
        check_isinstance(lit_numerote, LitNumerote)
        if lit_numerote.id in self.lits_numerotes:
            raise CrueError("Le lit numéroté `%s` est déjà présent" % lit_numerote.id)
        self.lits_numerotes.append(lit_numerote)

    def add_limite_geom(self, limite_geom):
        check_isinstance(limite_geom, LimiteGeom)
        if limite_geom.id in self.limites_geom:
            raise CrueError("La limite géométrique `%s` est déjà présente" % limite_geom.id)
        self.limites_geom.append(limite_geom)

    def interp_z(self, xt):
        return np.interp(xt, self.xz[:, 0], self.xz[:, 1])

    def interp_point(self, xt):
        if not self.lits_numerotes:
            raise CrueError('lits_numerotes has to be set before')
        xt_line = xt - self.lits_numerotes[0].xt_min
        diff = xt_line - self.geom_trace.length
        if diff > DISTANCE_TOL:
            logger.warn("Interpolation d'un point au-delà de la trace (écart=%sm) pour la %s" % (diff, self))
        if xt_line < -DISTANCE_TOL:
            logger.warn("Interpolation d'un point en-deça de la trace (écart=%sm) pour la %s" % (xt_line, self))
        return self.geom_trace.interpolate(xt_line)

    def get_coord(self, add_z=False):
        if self.xz is None:
            raise CrueError("`%s`: 3D trace could not be computed (xz is missing)!" % self)
        if self.geom_trace is None:
            raise CrueError("`%s`: 3D trace could not be computed (trace is missing)!" % self)
        coords = []
        for xt, z in self.xz_filtered:
            point = self.interp_point(xt)
            if add_z:
                coords.append((point.x, point.y, z))
            else:
                coords.append((point.x, point.y))
        return coords

    def get_is_bed_active_array(self):
        """/!\ Overestimation of active bed width"""
        xt = self.xz_filtered[:, 0]
        is_active = np.zeros(len(xt), dtype=bool)
        for lit in self.lits_numerotes:
            if 'G' in lit.id:
                bed_pos = np.logical_and(lit.xt_min < xt, xt <= lit.xt_max)
            else:
                bed_pos = np.logical_and(lit.xt_min <= xt, xt <= lit.xt_max)
            is_active[bed_pos] = lit.is_active
        return is_active

    def get_friction_coeff_array(self):
        """/!\ Overestimation of internal beds width"""
        xt = self.xz_filtered[:, 0]
        coeff = np.zeros(xt.shape[0], dtype=np.float)
        for lit in self.lits_numerotes:
            if 'G' in lit.id:
                bed_pos = np.logical_and(lit.xt_min < xt, xt <= lit.xt_max)
            else:
                bed_pos = np.logical_and(lit.xt_min <= xt, xt <= lit.xt_max)
            coeff[bed_pos] = lit.friction_law.loi_Fk[:, 1].mean()
        return coeff

    def has_xz(self):
        return self.xz is not None

    def has_trace(self):
        return self.geom_trace is not None

    def build_orthogonal_trace(self, axe_geom):
        """
        Section xp is supposed to be normalized (ie. xp is consistent with axe_geom length)
        """
        check_isinstance(axe_geom, LineString)
        xp = min(self.xp, axe_geom.length)  # in case xp is not consistant
        point = axe_geom.interpolate(xp)
        point_avant = axe_geom.interpolate(max(xp - DIFF_XP, 0.0))
        point_apres = axe_geom.interpolate(min(xp + DIFF_XP, axe_geom.length))
        distance = axe_geom.project(point_apres) - axe_geom.project(point_avant)
        u, v = (point_avant.y - point_apres.y) / distance, (point_apres.x - point_avant.x) / distance
        xt_list = [self.xz_filtered[0, 0], self.xz_filtered[-1, 0]]  # only extremities are written
        coords = [(point.x + (xt - self.xt_axe) * u, point.y + (xt - self.xt_axe) * v) for xt in xt_list]
        self.geom_trace = LineString(coords)

    def summary(self):
        text = '%s:' % self
        if self.has_xz():
            text += ' %i points' % len(self.xz)
        if self.has_trace():
            text += ' (%0.2f m)' % self.geom_trace.length
        return text

    def __repr__(self):
        return super().__repr__()


class SectionIdem(Section):
    """
    SectionIdem
    - parent_section <SectionProfil>: parent (= initial/reference) section
    - dz <float>: vertical shift (in meters)
    """

    def __init__(self, nom_section, parent_section, dz=0.0):
        super().__init__(nom_section)
        check_isinstance(parent_section, SectionProfil)
        self.parent_section = parent_section
        self.dz = dz

    def get_as_sectionprofil(self):
        """
        Return a SectionProfil instance from the original section
        """
        new_section = deepcopy(self.parent_section)
        new_section.id = self.id
        new_section.xp = self.xp
        new_section.xz[:, 1] += self.dz
        return new_section


class SectionInterpolee(Section):
    """
    SectionInterpolee
    """
    pass


class SectionSansGeometrie(Section):
    """
    SectionSansGeometrie
    """
    pass
