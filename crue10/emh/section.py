from copy import deepcopy

from crue10.utils import CrueError, logger


class Section:
    def __init__(self, nom_section):
        self.id = nom_section

    def __repr__(self):
        return '%s #%s:' % (self.__class__.__name__, self.id)


class SectionProfil(Section):
    def __init__(self, nom_section, nom_profilsection):
        super().__init__(nom_section)
        self.nom_profilsection = nom_profilsection
        self.xp_axe = 0
        self.xz = None
        self.geom_trace = None

    def set_xp_axe(self, xp_axe):
        self.xp_axe = xp_axe

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

    def __repr__(self):
        text = 'SectionProfil #%s:' % self.id
        if self.has_xz():
            text += ' %i points' % len(self.xz)
        if self.has_trace():
            text += ' (%0.2f m)' % self.geom_trace.length
        return text


class SectionIdem(Section):
    def __init__(self, nom_section):
        super().__init__(nom_section)
        self.nom_section = nom_section
        self.section_ori = None
        self.dz = None

    def set_as_profil(self, section, dz):
        new_section = deepcopy(section)
        #TODO apply dz translation
        return new_section
