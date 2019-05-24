from shapely.affinity import translate
from shapely.geometry import Point

from .section import SectionProfil
from crue10.utils import logger


DIFF_XP_TO_WARN = 20.0  # m


class Branche:
    """
    Branche
    - id <str>: branch identifier
    - type <int>: branch type (a key from `Branche.TYPES`)
    - noeud_amont <crue10.emh.noeud.Noeud>: upstream node
    - noeud_aval <crue10.emh.noeud.Noeud>: downstream node
    - sections <[crue10.emh.section.Section]>: list of sections
    """
    TYPES = {
        1: 'BranchePdc',
        2: 'BrancheSeuilTransversal',
        4: 'BrancheSeuilLateral',
        5: 'BrancheOrifice',
        6: 'BrancheStrickler',
        14: 'BrancheBarrageGenerique',
        15: 'BrancheBarrageFilEau',
        20: 'BrancheSaintVenant'
    }

    # Branch types whose sections (at least 2) have a geometry
    TYPES_WITH_GEOM = [2, 6, 15, 20]

    def __init__(self, nom_branche, noeud_amont, noeud_aval, branch_type, is_active=True):
        self.id = nom_branche
        self.type = branch_type
        self.is_active = is_active
        self.geom = None
        self.noeud_amont = noeud_amont
        self.noeud_aval = noeud_aval
        self.sections = []

    @staticmethod
    def get_id_type_from_name(branch_type_name):
        for type_id, type_name in Branche.TYPES.items():
            if type_name == branch_type_name:
                return type_id
        return None

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
        Recompute section xp to correspond to geometric distance (original values are taken from drso).
        Last section xp will correspond exactly to the branch length.
        """
        xp_max = self.sections[-1].xp
        length = self.geom.length
        if abs(xp_max - length) > DIFF_XP_TO_WARN:
            logger.warn("La longueur de la branche `%s` est estimée à %.2fm (non pas %.2fm)." % (self.id, length, xp_max))
        for i, section in enumerate(self.sections):
            try:
                section.xp = section.xp * length / xp_max
            except ZeroDivisionError:
                section.xp = (i / (len(self.sections) - 1)) * length

    def __repr__(self):
        return "Branche #%s: %s -> %s (%i sections)" % (self.id, self.noeud_amont, self.noeud_aval, len(self.sections))
