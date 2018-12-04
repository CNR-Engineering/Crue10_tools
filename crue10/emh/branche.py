from shapely.affinity import translate
from shapely.geometry import Point

from .section import SectionProfil
from crue10.utils import logger


DIFF_XP_TO_WARN = 20.0  # m


class Branche:
    """
    Branche
    - id <str>: branch identifier
    - noeud_amont <crue10.emh.noeud.Noeud>: upstream node
    - noeud_aval <crue10.emh.noeud.Noeud>: downstream node
    - sections <[crue10.emh.section.Section]>: list of sections
    """
    def __init__(self, nom_branche, noeud_amont, noeud_aval):
        self.id = nom_branche
        self.geom = None
        self.noeud_amont = noeud_amont
        self.noeud_aval = noeud_aval
        self.sections = []

    def add_section(self, section, xp):
        section.xp = xp
        self.sections.append(section)

    def set_geom(self, geom):
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
        Normalize section xp by the branch length to be consistent with geometry
        """
        xp_max = self.sections[-1].xp
        length = self.geom.length
        if abs(xp_max - length) > DIFF_XP_TO_WARN:
            logger.warn("La longueur de la branche est %f (non pas %f)." % (length, xp_max))
        for section in self.sections:
            section.xp = section.xp * length / xp_max

    def __repr__(self):
        return "Branche #%s: %s -> %s (%i sections)" % (self.id, self.noeud_amont, self.noeud_aval, len(self.sections))
