# coding: utf-8
"""
Classes for `Casier` in major bed (floodplain):
- ProfilCasier
- Casier

Not supported yet:
- TypeDPTGCasiers: SplanBati, ZBatiTotal (dptg.xml)
"""
import numpy as np
from shapely.geometry import LinearRing

from crue10.emh.noeud import Noeud
from crue10.utils import check_isinstance, check_preffix, CrueError


class ProfilCasier:
    """
    ProfilCasier
    - id <str>: profil casier identifier
    - distance <float>: applied length (or width) in meters
    - xz <2D-array>: ndarray(dtype=float, ndim=2)
        Array containing series of transversal abscissa and elevation (first axis should be strictly increasing)
    - xt_min <float>: first curvilinear abscissa (for LitUtile)
    - xt_max <float>: last curvilinear abscissa (for LitUtile)
    - comment <str>: optional text explanation
    """

    DEFAULT_COORDS = np.array([(0, 0), (50, 0), (100, 0)])

    def __init__(self, nom_profil_casier):
        check_preffix(nom_profil_casier, 'Pc_')
        self.id = nom_profil_casier
        self.distance = 0.0
        self.xz = None
        self.xt_min = -1.0
        self.xt_max = -1.0
        self.comment = ''

        self.set_xz(ProfilCasier.DEFAULT_COORDS)

    def set_xz(self, array):
        check_isinstance(array, np.ndarray)
        self.xz = array
        self.xt_min = self.xz[0, 0]
        self.xt_max = self.xz[-1, 0]

    def interp_z(self, xt):
        if xt < self.xt_min or xt > self.xt_max:
            raise CrueError("xt=%f is ouside range [%f, %f] for %s" % (xt, self.xt_min, self.xt_max, self))
        return np.interp(xt, self.xz[:, 0], self.xz[:, 1])

    def __str__(self):
        return "ProfilCasier #%s" % self.id


class Casier:
    """
    Casier (or storage area/reservoir)
    - id <str>: casier identifier
    - is_active <bool>: True if its node is active
    - geom <shapely.geometry.LinearRing>: polygon
    - noeud <Noeud>: related node
    - profils_casier <[ProfilCaser]>: profils casier (usually only one)
    - CoefRuis <float>: "coefficient modulation du débit linéique de ruissellement"
    - comment <str>: optional text explanation
    """

    def __init__(self, nom_casier, noeud, is_active=True):
        check_preffix(nom_casier, 'Ca_')
        check_isinstance(noeud, Noeud)
        self.id = nom_casier
        self.is_active = is_active
        self.geom = None
        self.noeud = noeud
        self.profils_casier = []
        self.CoefRuis = 0.0
        self.comment = ''

    def set_geom(self, geom):
        check_isinstance(geom, LinearRing)
        if geom.has_z:
            raise CrueError("La trace du %s ne doit pas avoir de Z !" % self)
        self.geom = geom

    def add_profil_casier(self, profil_casier):
        check_isinstance(profil_casier, ProfilCasier)
        self.profils_casier.append(profil_casier)

    def __str__(self):
        return "Casier #%s" % self.id
