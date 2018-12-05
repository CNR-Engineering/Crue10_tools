

class Noeud:
    """
    Noeud
    - id <str>: node identifier
    - geom <shapely.geometry.Point>: node position
    """
    def __init__(self, nom_noeud):
        self.id = nom_noeud
        self.geom = None

    def set_geom(self, geom):
        self.geom = geom

    def __str__(self):
        return "Noeud #%s" % self.id
