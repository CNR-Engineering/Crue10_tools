"""
Classes for junctions located in minor or major beds:
- Noeud
"""


class Noeud:
    """
    Noeud
    - id <str>: node identifier
    - geom <shapely.geometry.Point>: node position
    - comment <str>: optional text explanation
    """
    def __init__(self, nom_noeud):
        self.id = nom_noeud
        self.geom = None
        self.comment = ''

    def set_geom(self, geom):
        self.geom = geom

    def __str__(self):
        return "Noeud #%s" % self.id
