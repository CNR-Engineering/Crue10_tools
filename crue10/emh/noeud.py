

class Noeud:
    def __init__(self, nom_noeud):
        self.id = nom_noeud
        self.geom = None

    def __str__(self):
        return "Noeud #%s" % self.id
