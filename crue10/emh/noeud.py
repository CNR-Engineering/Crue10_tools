# coding: utf-8
"""
Class for junctions located in minor or major beds
"""
from shapely.geometry import Point

from crue10.utils import check_isinstance, check_preffix, ExceptionCrue10


class Noeud:
    """
    Noeud

    :param id: nom du noeud
    :type id: str
    :param geom: position du noeud
    :type geom: shapely.geometry.Point
    :param comment: text optionnel
    :type comment: str
    """

    def __init__(self, nom_noeud):
        """
        :param nom_noeud: nom du noeud
        :type nom_noeud: str
        """
        check_preffix(nom_noeud, 'Nd_')
        self.id = nom_noeud
        self.geom = None
        self.comment = ''

    def set_geom(self, geom):
        """Affecter la géométrie du noeud

        :param geom: point correspondant à la position du noeud
        :type geom: shapely.geometry.Point
        """
        check_isinstance(geom, Point)
        if geom.has_z:
            raise ExceptionCrue10("La géométrie du %s ne doit pas avoir de Z !" % self)
        self.geom = geom

    def validate(self):
        errors = []
        if len(self.id) > 32:  # valid.nom.tooLong.short
            errors.append((self, "Le nom est trop long, il d\u00e9passe les 32 caract\u00e8res"))
        return errors

    def __repr__(self):
        return "Noeud #%s" % self.id
