# coding: utf-8
"""
Classes for junctions located in minor or major beds:
- Noeud
"""
from shapely.geometry import Point

from crue10.utils import check_isinstance, check_preffix


class Noeud:
    """
    Noeud
    - id <str>: node identifier
    - geom <shapely.geometry.Point>: node position
    - comment <str>: optional text explanation
    """

    def __init__(self, nom_noeud):
        check_preffix(nom_noeud, 'Nd_')
        self.id = nom_noeud
        self.geom = None
        self.comment = ''

    def set_geom(self, geom):
        check_isinstance(geom, Point)
        self.geom = geom

    def __repr__(self):
        return "Noeud #%s" % self.id
