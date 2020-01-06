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
from crue10.utils import check_isinstance, check_preffix, CrueError, logger


DX = 0.1


def get_negative_area(x_array, y_array):
    """
    Integrate negative area (use composite trapezoidal rule with y_array < 0)
    :param x_array: 1d-array with x values
    :param y_array: 1d-array with y values
    :return: float
    """
    negative_area = 0
    for x1, y1, x2, y2 in zip(x_array, y_array, x_array[1:], y_array[1:]):
        if y1 <= 0:
            if y2 <= 0:
                negative_area += (x2 - x1) * abs(y1 + y2) / 2
            else:  # y2 > y1
                x_inter = np.interp(0.0, [y1, y2], [x1, x2], left=np.nan, right=np.nan)
                negative_area += (x_inter - x1) * abs(y1) / 2
        else:
            if y2 < 0:  # y1 > y2
                x_inter = np.interp(0.0, [y2, y1], [x2, x1], left=np.nan, right=np.nan)
                negative_area += (x2 - x_inter) * abs(y2) / 2
            else:
                pass  # fully positive
    return negative_area


class ProfilCasier:
    """
    ProfilCasier
    - id <str>: profil casier identifier
    - distance <float>: applied length (or width) in meters
    - xz <2D-array>: ndarray(dtype=float, ndim=2)
        Array containing series of lateral abscissa and elevation (first axis should be strictly increasing)
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
        if any(x > y for x, y in zip(array[:, 0], array[1:, 0])):
            raise CrueError("Les valeurs de xt ne sont pas strictement croissantes %s" % array[:, 0])
        self.xz = array
        self.xt_min = self.xz[0, 0]
        self.xt_max = self.xz[-1, 0]

    def interp_z(self, xt):
        if xt < self.xt_min or xt > self.xt_max:
            raise CrueError("xt=%f en dehors de la plage [%f, %f] pour %s" % (xt, self.xt_min, self.xt_max, self))
        return np.interp(xt, self.xz[:, 0], self.xz[:, 1])

    def compute_surface(self, z):
        return get_negative_area(self.xz[:, 0], self.xz[:, 1] - z)

    def compute_volume(self, z):
        return self.compute_surface(z) * self.distance

    def __str__(self):
        return "ProfilCasier #%s: distance = %f m, Z dans [%f, %f]" \
               % (self.id, self.distance, self.xz[:, 1].min(), self.xz[:, 1].max())


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

    def sum_distances(self):
        distance = 0
        for profil_casier in self.profils_casier:
            distance += profil_casier.distance
        return distance

    def compute_volume(self, z):
        volume = 0
        for profil_casier in self.profils_casier:
            volume += profil_casier.compute_volume(z)
        return volume

    def compute_surface(self, z):
        return self.compute_volume(z) / self.sum_distances()

    def merge_profil_casiers(self):
        """Replace multiple ProfilCasiers by a combined ProfilCasier giving a similar volume law"""
        if len(self.profils_casier) > 2:
            # Extract a sequence of bottom elevation
            z_array_combine = np.array([], dtype=np.float)
            for i, pc in enumerate(self.profils_casier):
                z_array = np.sort(pc.xz[:, 1])
                z_array_combine = np.concatenate((z_array_combine, z_array), axis=0)
            z_array_combine = np.sort(np.unique(z_array_combine))

            # Compute corresponding volumes
            volumes = []
            for z in z_array_combine:
                volume = self.compute_volume(z)
                volumes.append(volume)

            # Build a new ProfilCasier
            new_name = self.profils_casier[0].id
            new_profil_casier = ProfilCasier(new_name)
            new_profil_casier.distance = self.sum_distances()

            # Set its xz array
            new_xz = []
            xt = 0.0
            new_xz.append((xt, z_array_combine[0]))
            for i, (z1, z2, vol1, vol2) in enumerate(zip(z_array_combine, z_array_combine[1:], volumes, volumes[1:])):
                xt = ((vol2 - vol1) / self.sum_distances()) / (z2 - z1)
                new_xz.append((xt - DX, z1))
                new_xz.append((xt, z2))
            new_profil_casier.set_xz(np.array(new_xz))

            # Clear and add ProfilCasier
            self.profils_casier = []
            self.add_profil_casier(new_profil_casier)
        else:
            logger.debug("Le %s n'est pas fusionné car il a moins de 2 ProfilCasiers" % self)

    def __str__(self):
        return "Casier #%s" % self.id
