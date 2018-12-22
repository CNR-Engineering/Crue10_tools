from copy import deepcopy
from shapely.geometry import LineString

from crue10.utils import CrueError, logger


DIFF_XP = 0.1  # m


class Section:
    """
    Section
    - id <str>: section identifier
    - xp <float>: curvilinear abscissa of section on its associated branch
    """
    def __init__(self, nom_section):
        self.id = nom_section
        self.xp = -1

    def __repr__(self):
        return '%s #%s:' % (self.__class__.__name__, self.id)


class SectionProfil(Section):
    """
    SectionProfil
    - nom_profilsection <str>: profil section identifier (should start with `Ps_`)
    - xt_axe <float>: transversal position of hydraulic axis
    - xz <2D-array>: ndarray(dtype=float, ndim=2)
        Array containing series of transversal abscissa and elevation (first axis should be sctricly increasing)
    - geom_trace <LineString>: polyline section trace
    """
    def __init__(self, nom_section, nom_profilsection):
        super().__init__(nom_section)
        self.nom_profilsection = nom_profilsection
        self.xt_axe = 0  # curvilinear abscissa of hydraulic axis intersection
        self.xz = None
        self.geom_trace = None

    def set_xt_axe(self, xt_axe):
        self.xt_axe = xt_axe

    def set_xz(self, coords):
        self.xz = coords

    def set_trace(self, trace):
        self.geom_trace = trace

    def get_coord_3d(self):
        if self.xz is None or self.geom_trace is None:
            raise CrueError("`%s`: 3D trace could not be computed!" % self)
        min_xt = self.xz[:, 0].min()
        range_xt = self.xz[:, 0].max() - min_xt
        diff_xt = range_xt - self.geom_trace.length
        if abs(diff_xt) > 1e-2:
            logger.warn("Écart de longeur pour la section %s: %s" % (self, diff_xt))
        coords = []
        for x, z in self.xz:
            point = self.geom_trace.interpolate(x - min_xt)
            coords.append((point.x, point.y, z))
        return coords

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
        text = 'SectionProfil #%s:' % self.id
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
    def __init__(self, nom_section):
        super().__init__(nom_section)
