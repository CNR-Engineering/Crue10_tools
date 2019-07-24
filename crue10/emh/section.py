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

Not supported yet:
- Fente (dptg.xml)
- SectionProfil is truncated on "usefull width" (TODO)
"""
import abc
from builtins import super  # python2 compatibility, requires module `future`
from copy import deepcopy
import numpy as np
from shapely.geometry import LineString

from crue10.utils import CrueError, logger


# ABC below is compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})

DIFF_XP = 0.1  # m


class FrictionLaw:
    """
    Friction law (Strickler coefficient could vary with Z elevation)
    - id <str>: friction law identifier
    - type <str>: friction law type
    - loi_Fk <2D-array>: ndarray(dtype=float, ndim=2) with Stricker coefficient varying with elevation
    """
    def __init__(self, id, type, loi_Fk):
        self.id = id
        self.type = type
        self.loi_Fk = loi_Fk


class LitNumerote:
    """
    Lit numéroté
    - id <str>: bed identifier
    - xt_min <str>: first curvilinear abscissa
    - xt_max <str>: first curvilinear abscissa
    - friction_law <FrictionLaw>: friction law
    """
    BED_NAMES = ['Lt_StoD', 'Lt_MajD', 'Lt_Mineur', 'Lt_MajG', 'Lt_StoG']
    LIMIT_NAMES = ['RD', 'StoD-MajD', 'MajD-Min', 'Min-MajG', 'MajG-StoG', 'RG']

    def __init__(self, id, xt_min, xt_max, friction_law):
        self.id = id
        self.xt_min = xt_min
        self.xt_max = xt_max
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
    - geom_trace <LineString>: polyline section trace
    - lits_numerotes <[LitNumerote]>: lits numérotés
    - limites_geom <[LimiteGeom]>: limites géométriques (thalweg, axe hydraulique...)
    """
    def __init__(self, nom_section, nom_profilsection):
        super().__init__(nom_section)
        self.nom_profilsection = nom_profilsection
        self.xz = None
        self.geom_trace = None
        self.lits_numerotes = []
        self.limites_geom = []

    @property
    def xt_axe(self):
        """Curvilinear abscissa of hydraulic axis intersection"""
        for limite in self.limites_geom:
            if limite.id == 'Et_AxeHyd':
                return limite.xt
        raise CrueError("Limite 'Et_AxeHyd' could not be found for %s" % self)

    def set_xz(self, coords):
        self.xz = coords

    def set_trace(self, trace):
        if not self.lits_numerotes:
            raise CrueError('xz has to be set before (to check consistancy)')
        if not isinstance(trace, LineString):
            raise CrueError("Le type de la trace de la %s n'est pas supporté : %s !" % (self, type(trace)))
        if trace.has_z:
            raise CrueError("La trace de la %s ne doit pas avoir de Z !" % self)
        self.geom_trace = trace
        # Display a warning if geometry is not consistent with self.xz array
        min_xt = self.xz[:, 0].min()
        range_xt = self.xz[:, 0].max() - min_xt
        diff_xt = range_xt - self.geom_trace.length
        if abs(diff_xt) > 1e-2:
            logger.warn("Écart de longueur pour la section %s: %s" % (self, diff_xt))

    def add_lit_numerote(self, lit_numerote):
        self.lits_numerotes.append(lit_numerote)

    def add_limite_geom(self, limite_geom):
        self.limites_geom.append(limite_geom)

    def interp_z(self, xt):
        return np.interp(xt, self.xz[:, 0], self.xz[:, 1])

    def interp_point(self, xt):
        if not self.lits_numerotes:
            raise CrueError('lits_numerotes has to be set before')
        return self.geom_trace.interpolate(xt - self.lits_numerotes[0].xt_min)

    def get_coord(self, add_z=False):
        if self.xz is None:
            raise CrueError("`%s`: 3D trace could not be computed (xz is missing)!" % self)
        if self.geom_trace is None:
            raise CrueError("`%s`: 3D trace could not be computed (trace is missing)!" % self)
        coords = []
        for x, z in self.xz:
            point = self.interp_point(x)
            if add_z:
                coords.append((point.x, point.y, z))
            else:
                coords.append((point.x, point.y))
        return coords

    def get_is_bed_active_array(self):
        """/!\ Overestimation of active bed width"""
        xt = self.xz[:, 0]
        is_active = np.zeros(len(xt), dtype=bool)
        for lit in self.lits_numerotes:
            if 'G' in lit.id:
                bed_pos = np.logical_and(lit.xt_min < xt, xt < lit.xt_max)
            else:
                bed_pos = np.logical_and(lit.xt_min <= xt, xt <= lit.xt_max)
            is_active[bed_pos] = lit.is_active
        return is_active

    def get_friction_coeff_array(self):
        xt = self.xz[:, 0]
        coeff = np.zeros(self.xz.shape[0], dtype=np.float)
        for lit in self.lits_numerotes:
            if 'G' in lit.id:
                bed_pos = np.logical_and(lit.xt_min < xt, xt < lit.xt_max)
            else:
                bed_pos = np.logical_and(lit.xt_min <= xt, xt <= lit.xt_max)
            coeff[bed_pos] = lit.friction_law.array[:, 1].mean()
        return coeff

    def has_xz(self):
        return self.xz is not None

    def has_trace(self):
        return self.geom_trace is not None

    def build_orthogonal_trace(self, axe_geom):
        """
        Section xp is supposed to be normalized (ie. xp is consistent with axe_geom length)
        """
        point = axe_geom.interpolate(self.xp)
        point_avant = axe_geom.interpolate(max(self.xp - DIFF_XP, 0.0))
        point_apres = axe_geom.interpolate(min(self.xp + DIFF_XP, axe_geom.length))
        distance = axe_geom.project(point_apres) - axe_geom.project(point_avant)
        u, v = (point_avant.y - point_apres.y) / distance, (point_apres.x - point_avant.x) / distance
        xt_list = [self.xz[:, 0].min(), self.xz[:, 0].max()]  # only extremities are written
        coords = [(point.x + (xt - self.xt_axe) * u, point.y + (xt - self.xt_axe) * v) for xt in xt_list]
        self.geom_trace = LineString(coords)

    def __repr__(self):
        text = super().__repr__() + ':'
        if self.has_xz():
            text += ' %i points' % len(self.xz)
        if self.has_trace():
            text += ' (%0.2f m)' % self.geom_trace.length
        return text


class SectionIdem(Section):
    """
    SectionIdem
    - section_ori <SectionProfil>: original (= reference) section
    - dz <float>: vertical shift (in meters)
    """
    def __init__(self, nom_section):
        super().__init__(nom_section)
        self.section_ori = None
        self.dz = None

    def get_as_sectionprofil(self):
        """
        Return a SectionProfil instance from the original section
        """
        new_section = deepcopy(self.section_ori)
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
