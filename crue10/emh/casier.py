# coding: utf-8
"""
Classes pour les caiser du champ majeur :
    - ProfilCasier
    - Casier

TODO: Not supported yet: TypeDPTGCasiers: SplanBati, ZBatiTotal (dptg.xml)
"""
import numpy as np
from shapely.geometry import LinearRing

from crue10.emh.noeud import Noeud
from crue10.utils import check_isinstance, check_preffix, ExceptionCrue10, logger


DX = 0.1


def get_negative_area(x_array, y_array):
    """
    Integrate negative area (use composite trapezoidal rule with y_array < 0)

    :param x_array: x values
    :type x_array: 1d-array
    :param y_array: y values
    :yype y_array: 1d-array
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

    :param id: profil casier identifier
    :type id: str
    :param distance: applied length (or width) in meters
    :type distance: float
    :param xz: ndarray(dtype=float, ndim=2)
        Array containing series of lateral abscissa and elevation (first axis should be strictly increasing)
    :type xz: 2D-array
    :param xt_min: first curvilinear abscissa (for LitUtile)
    :type xt_min: float
    :param xt_max: last curvilinear abscissa (for LitUtile)
    :type xt_max: float
    :param comment: optional text explanation
    :type comment: str
    """

    DEFAULT_COORDS = np.array([(0, 0), (50, 0), (100, 0)])

    def __init__(self, nom_profil_casier):
        check_preffix(nom_profil_casier, 'Pc_')
        self.id = nom_profil_casier
        self.longueur = 0.0
        self.xz = None
        self.xt_min = -1.0
        self.xt_max = -1.0
        self.comment = ''

        self.set_xz(ProfilCasier.DEFAULT_COORDS)

    def set_longueur(self, longueur):
        self.longueur = longueur

    def set_xz(self, array):
        check_isinstance(array, np.ndarray)
        if any(x > y for x, y in zip(array[:, 0], array[1:, 0])):
            raise ExceptionCrue10("Les valeurs de xt ne sont pas strictement croissantes %s" % array[:, 0])
        self.xz = array
        self.xt_min = self.xz[0, 0]
        self.xt_max = self.xz[-1, 0]

    def interp_z(self, xt):
        if xt < self.xt_min or xt > self.xt_max:
            raise ExceptionCrue10("xt=%f en dehors de la plage [%f, %f] pour %s" % (xt, self.xt_min, self.xt_max, self))
        return np.interp(xt, self.xz[:, 0], self.xz[:, 1])

    def compute_surface(self, z):
        return get_negative_area(self.xz[:, 0], self.xz[:, 1] - z)

    def compute_volume(self, z):
        return self.compute_surface(z) * self.longueur

    def __str__(self):
        return "ProfilCasier #%s: longueur = %f m, Z dans [%f, %f]" \
               % (self.id, self.longueur, self.xz[:, 1].min(), self.xz[:, 1].max())


class Casier:
    """
    Casier (ou zone de stockage, réservoir)

    :param id: nom du casier
    :type id: str
    :param is_active: True if its node is active
    :type is_active: bool
    :param geom: polygon
    :type geom: shapely.geometry.LinearRing
    :param noeud_reference: related node
    :type noeud_reference: Noeud
    :param profils_casier: profils casier (usually only one)
    :type profils_casier: [ProfilCaser]
    :param CoefRuis: "coefficient modulation du débit linéique de ruissellement"
    :type CoefRuis: float
    :param comment: optional text explanation
    :type comment: str
    """

    def __init__(self, nom_casier, noeud, is_active=True):
        check_preffix(nom_casier, 'Ca_')
        check_isinstance(noeud, Noeud)
        self.id = nom_casier
        self.is_active = is_active
        self.geom = None
        self.noeud_reference = noeud
        self.profils_casier = []
        self.CoefRuis = 0.0
        self.comment = ''

    def set_geom(self, geom):
        """Affecter la géométrie du casier

        :param geom: polygone d'emprise du casier
        :type geom: shapely.geometry.LinearRing
        """
        check_isinstance(geom, LinearRing)
        if geom.has_z:
            raise ExceptionCrue10("La géométrie du %s ne doit pas avoir de Z !" % self)
        self.geom = geom

    def ajouter_profil_casier(self, profil_casier):
        """Ajouter le profil casier

        :param profil_casier: ProfilCasier
        """
        check_isinstance(profil_casier, ProfilCasier)
        self.profils_casier.append(profil_casier)

    def somme_longueurs(self):
        """
        :return: Somme les longueurs des branches
        """
        distance = 0
        for profil_casier in self.profils_casier:
            distance += profil_casier.longueur
        return distance

    def compute_volume(self, z):
        """Calculer le volume

        :param z: niveau d'eau
        :type z: float
        :return: volume
        :rtype: float
        """
        volume = 0
        for profil_casier in self.profils_casier:
            volume += profil_casier.compute_volume(z)
        return volume

    def compute_surface(self, z):
        """Calculer la surface

        :param z: niveau d'eau
        :type z: float
        :return: surface
        :rtype: float
        """
        return self.compute_volume(z) / self.somme_longueurs()

    def fusion_profil_casiers(self):
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
            new_profil_casier.longueur = self.somme_longueurs()

            # Set its xz array
            new_xz = []
            xt = 0.0
            new_xz.append((xt, z_array_combine[0]))
            for i, (z1, z2, vol1, vol2) in enumerate(zip(z_array_combine, z_array_combine[1:], volumes, volumes[1:])):
                xt = ((vol2 - vol1) / self.somme_longueurs()) / (z2 - z1)
                new_xz.append((xt - DX, z1))
                new_xz.append((xt, z2))
            new_profil_casier.set_xz(np.array(new_xz))

            # Clear and add ProfilCasier
            self.profils_casier = []
            self.ajouter_profil_casier(new_profil_casier)
        else:
            logger.debug("Le %s n'est pas fusionné car il a moins de 2 ProfilCasiers" % self)

    def get_min_z(self):
        """
        :return: niveau minimum des profils casiers synthétiques
        :rtype: float
        """
        min_z = float('inf')
        for profil_casier in self.profils_casier:
            min_z = min(min_z, profil_casier.xz[:, 1].min())
        return min_z

    def validate(self):
        errors = []
        if len(self.id) > 32:  # valid.nom.tooLong.short
            errors.append((self, "Le nom est trop long, il d\u00e9passe les 32 caract\u00e8res"))
        # TODO: Casier has at least one ProfilCasier
        return errors

    def __str__(self):
        return "Casier #%s" % self.id
