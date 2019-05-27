

class Casier:
    """
    Casier (or reversoir)
    - id <str>: casier identifier
    - geom <shapely.geometry.LinearRing>: polygon
    """
    def __init__(self, nom_casier, is_active=False):
        self.id = nom_casier
        self.is_active = is_active
        self.geom = None

    def set_geom(self, geom):
        self.geom = geom

    def __str__(self):
        return "Casier #%s" % self.id
