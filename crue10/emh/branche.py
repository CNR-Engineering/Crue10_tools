

class Branche:
    def __init__(self, nom_branche, noeud_amont, noeud_aval):
        self.id = nom_branche
        self.geom = None
        self.noeud_amont = noeud_amont
        self.noeud_aval = noeud_aval
        self.sections = []

    def add_section(self, section):
        self.sections.append(section)

    def set_geom(self, geom):
        self.geom = geom

    def __repr__(self):
        return "Branche #%s: %s -> %s (%i sections)" % (self.id, self.noeud_amont, self.noeud_aval, len(self.sections))
