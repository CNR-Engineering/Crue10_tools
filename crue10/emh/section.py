# coding: utf-8
"""
Classes pour les sections :

- :class:`LoiFrottement`
- :class:`LitNumerote`
- :class:`LimiteGeom`
- :class:`Section`

    - :class:`SectionProfil`
    - :class:`SectionIdem`
    - :class:`SectionInterpolee`
    - :class:`SectionSansGeometrie`
"""
import abc
from builtins import super  # Python2 fix (requires module `future`)
from copy import deepcopy
import numpy as np
from shapely.geometry import LineString, Point

from crue10.utils import check_isinstance, check_preffix, ExceptionCrue10, logger


# ABC below is compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})

DIFF_XP = 0.1  # m

DISTANCE_TOL = 0.01  # m


def extrap(x, xp, yp):
    """
    Interpolation linéaire (equivalente à `np.interp` with extrapolation)

    :param x: The x-coordinates at which to evaluate the interpolated values.
    :type x: The x-coordinates at which to evaluate the interpolated values
    :param xp: The x-coordinates of the data points, must be increasing
    :type xp: 1d-array
    :param yp: The y-coordinates of the data points, same length as xp
    :type xp: 1d-array
    :return: he interpolated values, same shape as x
    """
    y = np.interp(x, xp, yp)
    y = np.where(x < xp[0], yp[0]+(x-xp[0])*(yp[0]-yp[1])/(xp[0]-xp[1]), y)
    y = np.where(x > xp[-1], yp[-1]+(x-xp[-1])*(yp[-1]-yp[-2])/(xp[-1]-xp[-2]), y)
    return y


class LoiFrottement:
    """
    Loi de frottement (coefficient(s) de Strickler éventuellement variable(s) avec le niveau d'eau)

    :ivar id: nom de la loi de frottement
    :type id: str
    :ivar type: type de loi de frottement
    :type type: str
    :ivar loi_Fk: tableau de coefficients de Strickler fonction de la cote, shape=(nb_values, 2)
    :type loi_Fk: np.ndarray
    :ivar comment: optional text explanation
    :type comment: str
    """

    #: Types possibles de loi de frottement
    TYPES = ['FkSto', 'Fk']

    def __init__(self, nom_loi_frottement, type, comment=''):
        check_preffix(nom_loi_frottement, 'Fk')
        if type not in LoiFrottement.TYPES:
            raise NotImplementedError
        self.id = nom_loi_frottement
        self.loi_Fk = None
        self.type = type
        self.comment = comment

    def set_loi_Fk_values(self, loi_values):
        """
        Affecter le tableau de coefficients de Strickler fonction de la cote

        :param loi_values: tableau de coefficients de Strickler fonction de la cote
        :type loi_values: np.ndarray
        """
        check_isinstance(loi_values, np.ndarray)
        self.loi_Fk = loi_values

    def set_loi_constant_value(self, value):
        """
        Affecter la valeur de coefficient de Strickler (non variable avec la cote)

        :param value: coefficient de Strickler à affecter
        :type value: float
        """
        check_isinstance(value, float)
        self.loi_Fk[:, 1] = value

    def shift_loi_Fk_values(self, value):
        """
        Sommer le coefficient de Strickler avec la valeur souhaitée (positive ou négative)

        :param value: coefficient de Strickler à affecter
        :type value: float
        """
        check_isinstance(value, float)
        self.loi_Fk[:, 1] += value

    def get_loi_Fk_values(self):
        """
        :return: tableau de coefficients de Strickler fonction de la cote
        :rtype: np.ndarray
        """
        return self.loi_Fk[:, 1]

    def get_loi_Fk_value(self):
        """
        :return: valeur de coefficient de Strickler
        :rtype: float
        """
        values = self.get_loi_Fk_values()
        if len(values) != 1:
            raise ExceptionCrue10("La loi de frottement %s contient plus de 1 valeur, "
                                  "cette méthode n'est pas utilisable." % self.id)
        return values[0]


DEFAULT_FK_STO = LoiFrottement('FkSto_K0_0001', 'FkSto')
DEFAULT_FK_STO.set_loi_Fk_values(np.array([(0.0, 0.0)]))
DEFAULT_FK_MAJ = LoiFrottement('Fk_DefautMaj', 'Fk')
DEFAULT_FK_MAJ.set_loi_Fk_values(np.array([(-15.0, 8.0)]))
DEFAULT_FK_MIN = LoiFrottement('Fk_DefautMin', 'Fk')
DEFAULT_FK_MIN.set_loi_Fk_values(np.array([(-15.0, 8.0)]))


class LitNumerote:
    """
    Lit numéroté = intervalle entre 2 limites de lit

    :ivar id: identifiant du lit numéroté (une clé de `BED_NAMES`)
    :type id: str
    :ivar xt_min: première abscisse curviligne
    :type xt_min: float
    :ivar xt_max: dernière abscisse curviligne
    :vartype xt_max: float
    :ivar loi_frottement: loi de frottement
    :vartype loi_frottement: LoiFrottement
    """

    #: Ordre des lits nommés
    BED_NAMES = ['Lt_StoD', 'Lt_MajD', 'Lt_Mineur', 'Lt_MajG', 'Lt_StoG']

    #: Limites entre lits
    LIMIT_NAMES = ['RD', 'StoD-MajD', 'MajD-Min', 'Min-MajG', 'MajG-StoG', 'RG']

    def __init__(self, nom_lit, xt_min, xt_max, loi_frottement=None):
        """
        :param nom_lit: identifiant du lit numéroté (une clé de `BED_NAMES`)
        :type nom_lit: str
        :param xt_min: première abscisse curviligne
        :type xt_min: float
        :param xt_max: dernière abscisse curviligne
        :type xt_max: float
        :param loi_frottement: loi de frottement (si absent alors la loi par défaut est prise en fonction du type de lit)
        :type loi_frottement: LoiFrottement
        """
        if nom_lit not in LitNumerote.BED_NAMES:
            raise RuntimeError
        self.id = nom_lit
        self.xt_min = xt_min
        self.xt_max = xt_max
        if loi_frottement is None:
            if 'Sto' in nom_lit:
                loi_frottement = DEFAULT_FK_STO
            elif 'Maj' in nom_lit:
                loi_frottement = DEFAULT_FK_MAJ
            else:
                loi_frottement = DEFAULT_FK_MIN
        self.loi_frottement = loi_frottement

    @property
    def is_active(self):
        """Est un lit actif (= un lit mineur ou majeur)"""
        return 'Maj' in self.id or 'Min' in self.id

    @property
    def get_est_mineur(self):
        """Est un lit mineur"""
        return 'Min' in self.id

    def __repr__(self):
        return 'LitNumeroté #%s (%f -> %s)' % (self.id, self.xt_min, self.xt_max)


class LimiteGeom:
    """
    Limite géométrique

    :ivar id: nom de la limite
    :vartype id: str
    :ivar xt: abscisse curviligne
    :vartype xt: float
    """

    AXE_HYDRAULIQUE = 'Et_AxeHyd'
    THALWEG = 'Et_Thalweg'

    def __init__(self, id, xt):
        """
        :param id: nom de la limite
        :type id: str
        :param xt: abscisse curviligne
        :type xt: float
        """
        check_preffix(id, 'Et_')
        self.id = id
        self.xt = xt

    def __repr__(self):
        return 'Limite #%s (%f)' % (self.id, self.xt)


class Section(ABC):
    """
    Méthode abstraite pour les sections

    :ivar id: nom de la section
    :vartype id: str
    :ivar is_active: True si la section est connectée à une branche active => utilisé pour lire le fichier rcal
    :vartype is_active: bool
    :ivar xp: abscisse curviligne de la section le long de sa branche associée
    :vartype xp: float
    :ivar CoefPond: "coefficient de pondération amont/aval de la discrétisation de la perte de charge régulière J
        entre la section et sa suivante"
    :vartype CoefPond: float
    :ivar CoefConv: "coefficient de perte de charge ponctuelle en cas de convergence entre la section et sa
        suivante"
    :vartype CoefConv: float
    :ivar CoefDiv: "coefficient de perte de charge ponctuelle en cas de divergence entre la section et sa suivante"
    :vartype CoefDiv: float
    :ivar comment: commentaire optionnel
    :vartype comment: str
    """

    def __init__(self, nom_section):
        """
        :param nom_section: nom de la section
        :type nom_section: str        """
        self.id = nom_section
        self.is_active = False
        self.xp = -1
        self.CoefPond = 0.5
        self.CoefConv = 0.0
        self.CoefDiv = 0.0
        self.comment = ''

    def validate(self):
        """Valider"""
        errors = []
        if len(self.id) > 32:  # valid.nom.tooLong.short
            errors.append((self, "Le nom est trop long, il d\u00e9passe les 32 caract\u00e8res"))
        return errors

    def __repr__(self):
        return '%s #%s' % (self.__class__.__name__, self.id)


class SectionProfil(Section):
    """
    SectionProfil

    :ivar nom_profilsection: nom de la SectionProfil (doit commencer par `Ps_`)
    :vartype nom_profilsection: str
    :ivar comment_profilsection: commentaire du ProfilSection
    :vartype comment_profilsection: str
    :ivar xz: tableau avec les abscisses transversales et la cote (les abscisses doivent être strictement croissantes),
        shape=(nb_values, 2)
    :vartype xz: np.ndarray
    :ivar geom_trace: polyline de la trace de la section (entre les rives gauche et droite)
    :vartype geom_trace: shapely.geometry.LineString
    :ivar largeur_fente: largeur de la fente
    :vartype largeur_fente: float
    :ivar profondeur_fente: profondeur de la fente
    :vartype profondeur_fente: float
    :ivar lits_numerotes: lits numérotés
    :vartype lits_numerotes: list(LitNumerote)
    :ivar limites_geom: limites géométriques (thalweg, axe hydraulique...)
    :vartype limites_geom: list(LimiteGeom)
    """

    def __init__(self, nom_section, nom_profilsection=None):
        """
        :param nom_section: nom de la section
        :type nom_section: str
        :param nom_profilsection: nom du ProfilSection
        :type nom_profilsection: str
        """
        super().__init__(nom_section)
        self.nom_profilsection = ''
        self.comment_profilsection = ''
        self.set_profilsection_name(nom_profilsection)
        self.xz = None
        self.geom_trace = None
        self.largeur_fente = None
        self.profondeur_fente = None
        self.lits_numerotes = []
        self.limites_geom = []

    def set_profilsection_name(self, nom_profilsection=None):
        """
        Affecter le nom du ProfilSection

        :param nom_profilsection: nom du ProfilSection (si None alors il sera déterminé automatiquement)
        :type nom_profilsection: str
        """
        if nom_profilsection is None:
            self.nom_profilsection = 'Ps_' + self.id[3:]
        else:
            check_preffix(nom_profilsection, 'Ps_')
            self.nom_profilsection = nom_profilsection

    @property
    def xt_axe(self):
        """
        :return: Abscisse curviligne de l'axe hydraulique
        :rtype: float
        """
        for limite in self.limites_geom:
            if limite.id == 'Et_AxeHyd':
                return limite.xt
        raise ExceptionCrue10("La limite 'Et_AxeHyd' n'existe pas pour %s" % self)

    @property
    def is_avec_fente(self):
        """Dispose d'une fente"""
        return self.largeur_fente is not None and self.profondeur_fente is not None

    @property
    def xz_filtered(self):
        """
        :return: Tableau avec les abscisses transversales et la cote entre les rives gauche et droite
        :rtype: np.ndarray
        """
        return self.xz[np.logical_and(self.lits_numerotes[0].xt_min <= self.xz[:, 0],
                                      self.xz[:, 0] <= self.lits_numerotes[-1].xt_max), :]

    def set_xz(self, array):
        """
        Affecter le tableau avec les abscisses transversales et la cote

        :param array: tableau avec les abscisses transversales et la cote à affeter
        :type array: np.ndarray
        """
        check_isinstance(array, np.ndarray)
        new_array = array[0, :]
        duplicated_xt = []
        for (xt1, z1), (xt2, z2) in zip(array, array[1:]):
            if xt1 == xt2:
                duplicated_xt.append(xt2)
            else:
                new_array = np.vstack((new_array, [xt2, z2]))
        self.xz = new_array
        if any(x > y for x, y in zip(new_array[:, 0], new_array[1:, 0])):
            raise ExceptionCrue10("Les valeurs de xt ne sont pas croissantes (points doublons tolérés mais ignorés)")
        if duplicated_xt:
            logger.warn("%i points doublons ignorés pour %s: %s" % (len(duplicated_xt), self, duplicated_xt))

    def set_geom_trace(self, geom_trace):
        """
        Affecter la trace de la section

        :param geom_trace: polyline de la trace de la section (entre les rives gauche et droite)
        :type geom_trace: shapely.geometry.LineString
        """
        check_isinstance(geom_trace, LineString)
        if geom_trace.has_z:
            raise ExceptionCrue10("La trace de la %s ne doit pas avoir de Z !" % self)
        if not self.lits_numerotes:
            raise ExceptionCrue10('xz has to be set before (to check consistency)')
        self.geom_trace = geom_trace

        # Display a warning if geometry is not consistent with self.xz array
        range_xt = self.xz_filtered[:, 0].max() - self.xz_filtered[:, 0].min()
        diff_xt = range_xt - self.geom_trace.length
        if abs(diff_xt) > 1e-2:
            logger.warn("Écart de longueur pour la section %s: %s" % (self, diff_xt))

    def ajouter_fente(self, largeur, profondeur):
        """
        Ajouter (ou remplacer) la largeur et la profondeur de la fente

        :param largeur: largeur de la fente
        :type largeur: float
        :param profondeur: profondeur de la fente
        :type profondeur: float
        """
        if largeur <= 0:
            raise ExceptionCrue10("La largeur de fente doit être strictement positive")
        if profondeur <= 0:
            raise ExceptionCrue10("La profondeur de fente doit être strictement positive")
        self.largeur_fente = largeur
        self.profondeur_fente = profondeur

    def set_lits_numerotes(self, xt_list):
        """
        Affecter les 5 lits numérotés à partir de la liste ordonnée des 6 abscisses curvilignes

        :param xt_list: liste ordonnée des 6 abscisses curvilignes
        :type xt_list: list(float)
        """
        if len(xt_list) != 6:
            raise ExceptionCrue10("Il faut exactement 5 lits numérotés pour les affecter")
        if any(x > y for x, y in zip(xt_list, xt_list[1:])):
            raise ExceptionCrue10("Les valeurs de xt ne sont pas croissantes")
        self.lits_numerotes = []
        for bed_name, xt_min, xt_max in zip(LitNumerote.BED_NAMES, xt_list, xt_list[1:]):
            lit_numerote = LitNumerote(bed_name, xt_min, xt_max)
            self.lits_numerotes.append(lit_numerote)

    def ajouter_lit(self, lit_numerote):
        """
        Ajouter le lit numéroté

        :param lit_numerote: lit numéroter à ajouter
        :type lit_numerote: LitNumerote
        """
        check_isinstance(lit_numerote, LitNumerote)
        if lit_numerote.id in self.lits_numerotes:
            raise ExceptionCrue10("Le lit numéroté `%s` est déjà présent" % lit_numerote.id)
        self.lits_numerotes.append(lit_numerote)

    def ajouter_limite_geom(self, limite_geom):
        """
        Ajouter la limite géométrique

        :param limite_geom: limite géométrique à ajouter
        :type limite_geom: LimiteGeom
        """
        check_isinstance(limite_geom, LimiteGeom)
        if limite_geom.id in self.limites_geom:
            raise ExceptionCrue10("La limite géométrique `%s` est déjà présente" % limite_geom.id)
        self.limites_geom.append(limite_geom)

    def interp_z(self, xt):
        """
        Interpoler la cote à partir d'une absicisse donnée

        :param xt: abscisse curviligne
        :return: niveau interpolé
        :rtype: np.ndarray
        """
        return np.interp(xt, self.xz[:, 0], self.xz[:, 1])

    def interp_point(self, xt):
        """
        Interpolation et extrapolation (si en dehors des rives gauche et droite) d'un point le long de la trace

        :param xt: abscisse curviligne
        :type: float
        :rtype: shapely.geometry.Point
        """
        if not self.lits_numerotes:
            raise ExceptionCrue10('Les lits numerotés doivent être définis au préalable')
        xt_line = xt - self.lits_numerotes[0].xt_min
        diff = xt_line - self.geom_trace.length
        if diff > DISTANCE_TOL:
            logger.debug("Extrapolation d'un point au-delà de la trace (écart=%sm) pour la %s" % (diff, self))
        if xt_line < -DISTANCE_TOL:
            logger.debug("Extrapolation d'un point en-deça de la trace (écart=%sm) pour la %s" % (xt_line, self))

        # Get coordinates from trace
        x_array = np.array([x for x, _ in self.geom_trace.coords])
        y_array = np.array([y for _, y in self.geom_trace.coords])
        distances = np.zeros(len(x_array))
        distances[1:] = np.cumsum(np.sqrt(np.square(x_array[:-1] - x_array[1:]) +
                                          np.square(y_array[:-1] - y_array[1:])))

        # Remove duplicated in trace (distances are strictly increasing)
        to_keep = distances - np.roll(distances, 1) > 0
        to_keep[0] = True
        x_array = x_array[to_keep]
        y_array = y_array[to_keep]
        distances = distances[to_keep]

        # Extrapolate x and y
        x = extrap(xt_line, distances, x_array)
        y = extrap(xt_line, distances, y_array)
        return Point(x, y)

    def get_coord(self, add_z=False):
        """
        Obtenir les coordonnées (x, y) (ou (x, y, z)) des points composant le profil en travers

        :param add_z: prise en compte du z si True
        :return: list(float)
        """
        if self.xz is None:
            raise ExceptionCrue10("`%s`: 3D trace could not be computed (xz is missing)!" % self)
        if self.geom_trace is None:
            raise ExceptionCrue10("`%s`: 3D trace could not be computed (trace is missing)!" % self)
        coords = []
        for xt, z in self.xz_filtered:
            point = self.interp_point(xt)
            if add_z:
                coords.append((point.x, point.y, z))
            else:
                coords.append((point.x, point.y))
        return coords

    def get_is_bed_active_array(self):
        """Overestimation of active bed width"""
        xt = self.xz_filtered[:, 0]
        is_active = np.zeros(len(xt), dtype=bool)
        for lit in self.lits_numerotes:
            if 'G' in lit.id:
                bed_pos = np.logical_and(lit.xt_min < xt, xt <= lit.xt_max)
            else:
                bed_pos = np.logical_and(lit.xt_min <= xt, xt <= lit.xt_max)
            is_active[bed_pos] = lit.is_active
        return is_active

    def get_friction_coeff_array(self):
        """Overestimation of internal beds width"""
        xt = self.xz_filtered[:, 0]
        coeff = np.zeros(xt.shape[0], dtype=np.float)
        for lit in self.lits_numerotes:
            if 'G' in lit.id:
                bed_pos = np.logical_and(lit.xt_min < xt, xt <= lit.xt_max)
            else:
                bed_pos = np.logical_and(lit.xt_min <= xt, xt <= lit.xt_max)
            coeff[bed_pos] = lit.loi_frottement.loi_Fk[:, 1].mean()
        return coeff

    def get_premier_lit_numerote(self, nom):
        """
        Obtenir le premier lit numéroté demandé

        :param nom: nom du lit à rechercher
        :type nom: str
        :rtype: LitNumerote
        """
        for lit in self.lits_numerotes:
            if lit.id == nom:
                return lit
        raise ExceptionCrue10("Aucun lit `%s` pour la %s" % (nom, self))

    def get_dernier_lit_numerote(self, nom):
        """
        Obtenir le dernier lit numéroté demandé

        :param nom: nom du lit à rechercher
        :type nom: str
        :rtype: LitNumerote
        """
        for lit in reversed(self.lits_numerotes):
            if lit.id == nom:
                return lit
        raise ExceptionCrue10("Aucun lit `%s` pour la %s" % (nom, self))

    def get_xt_limite_lit(self, nom_limite):
        """
        Obtenir l'abscisse curviligne de la limite de lit recherchée

        :param nom_limite: nom de la limite de lit à rechercher
        :type nom_limite: str
        :return: abscisse curviligne
        :rtype: float
        """
        idx_limite = LitNumerote.LIMIT_NAMES.index(nom_limite)
        if idx_limite == 0:
            return self.get_premier_lit_numerote(LitNumerote.BED_NAMES[0]).xt_min
        else:
            nom_lit = LitNumerote.BED_NAMES[idx_limite - 1]
            return self.get_dernier_lit_numerote(nom_lit).xt_max

    def get_limite_geom(self, nom):
        """
        Obtenir l'abscisse curviligne de la limite géométrique recherchée

        :param nom_limite: nom de la limite géométrique à rechercher
        :type nom_limite: str
        :return: abscisse curviligne
        :rtype: float
        """
        for limite in self.limites_geom:
            if limite.id == nom:
                return limite
        raise ExceptionCrue10("La limite `%s` n'exsite pas pour la %s" % (nom, self))

    def has_xz(self):
        return self.xz is not None

    def has_trace(self):
        return self.geom_trace is not None

    def build_orthogonal_trace(self, branche_geom):
        """
        Construire une trace orthogonale (ligne droite entre les rives gauche et droite) à la trace de la branche

        Attention: le `xp` de la section est supposé avoir été normalisé
        (ie. xp est cohérent avec la longueur de axe_geom)

        :param branche_geom: trace de la branche
        :type branche_geom: shapely.geometry.LineString
        """
        check_isinstance(branche_geom, LineString)
        xp = min(self.xp, branche_geom.length)  # in case xp is not consistant
        point = branche_geom.interpolate(xp)
        point_avant = branche_geom.interpolate(max(xp - DIFF_XP, 0.0))
        point_apres = branche_geom.interpolate(min(xp + DIFF_XP, branche_geom.length))
        distance = branche_geom.project(point_apres) - branche_geom.project(point_avant)
        u, v = (point_avant.y - point_apres.y) / distance, (point_apres.x - point_avant.x) / distance
        xt_list = [self.xz_filtered[0, 0], self.xz_filtered[-1, 0]]  # only extremities are written
        coords = [(point.x + (xt - self.xt_axe) * u, point.y + (xt - self.xt_axe) * v) for xt in xt_list]
        self.geom_trace = LineString(coords)

    def merge_consecutive_lit_numerotes(self):
        """
        Les `LitNumerote` consécutifs avec les mêmes `LitNomme` sont fusionnés en un seul et `LitNumerote` plus large
        """
        xt_list = [self.lits_numerotes[0].xt_min]
        for lit1, lit2 in zip(self.lits_numerotes[:-1], self.lits_numerotes[1:]):
            if lit1.id != lit2.id:
                assert lit1.xt_max == lit2.xt_min
                xt_list.append(lit1.xt_max)
        xt_list.append(self.lits_numerotes[-1].xt_max)
        self.set_lits_numerotes(xt_list)

    def get_min_z(self):
        """
        :return: cote minimale du profil en travers
        :rtype: float
        """
        return self.xz[:, 1].min()

    def validate(self):
        """
        Valider

        TODO: validate.thalweg.NotInLitMineur, validate.etiquette.definedSeveralTimes
        """
        errors = super().validate()

        # Lits numérotés
        if len(self.lits_numerotes) == 0:
            errors.append((self, "Aucun LitNumerote"))  # io.dptg.convert.noLit.error
        else:
            for nom_lit in LitNumerote.BED_NAMES:
                try:
                    self.get_premier_lit_numerote(nom_lit)
                except ExceptionCrue10:
                    errors.append((self, 'le LitNumerote `%s` manque' % nom_lit))
            for lit in self.lits_numerotes:
                if lit.xt_min not in self.xz[:, 0]:  # validate.lit.limDebNotFound
                    errors.append((self, "LitNumerote %s: la limite de d\u00e9but n'est pas un point du profil."
                                   % lit.id))
                if lit.xt_min > lit.xt_max:  # validate.lit.limFinMustBeGreatedThanLitDeb
                    errors.append((self, "LitNumerote %s: la limite de fin est inf\u00e9rieure \u00e0"
                                         " la limite de d\u00e9but" % lit.id))
                if lit.xt_max not in self.xz[:, 0]:  # validate.lit.limFinNotFound
                    errors.append((self, "LitNumerote %s: la limite de fin n'est pas un point du profil."
                                   % lit.id))
                if set([lit.id for lit in self.lits_numerotes]) != set(LitNumerote.BED_NAMES):
                    # profil.editionValidation.order.error
                    errors.append((self, "L''ordre de LitNomme n''est pas valide. Attendu: %s"
                                   % LitNumerote.BED_NAMES))

        # Cas particulier du lit mineur
        try:
            premier_lit_mineur = self.get_premier_lit_numerote('Lt_Mineur')
            dernier_lit_mineur = self.get_dernier_lit_numerote('Lt_Mineur')
            mineur_deb, mineur_fin = premier_lit_mineur.xt_min, dernier_lit_mineur.xt_max
            if mineur_deb >= mineur_fin:
                errors.append((self, "Le lit mineur est de dimension nulle"))  # validate.lit.litMineurNull
        except ExceptionCrue10:
            pass  # validate.lit.litMineurNotFound est un cas particulier vu avant

        # Limites géométriques
        try:
            limite_axe = self.get_limite_geom('Et_AxeHyd')
            try:
                if not(self.get_premier_lit_numerote('Lt_Mineur').xt_min <= limite_axe.xt <=
                       self.get_dernier_lit_numerote('Lt_Mineur').xt_max):
                    # validate.axeHyd.NotInLitMineur
                    errors.append((self, "L'axe hydraulique n'appartient pas au lit mineur"))
            except ExceptionCrue10:
                pass  # Lit numéroté mineur manque, déjà reporté plus haut

        except ExceptionCrue10:
            errors.append((self, "L'axe hydraulique n'est pas défini"))

        return errors

    def summary(self):
        text = '%s:' % self
        if self.has_xz():
            text += ' %i points' % len(self.xz)
        if self.has_trace():
            text += ' (%0.2f m)' % self.geom_trace.length
        return text

    def __repr__(self):
        return super().__repr__()


class SectionIdem(Section):
    """
    SectionIdem

    :ivar section_reference: section de référence (ou source)
    :vartype section_reference: SectionProfil
    :ivar dz_section_reference: décalage vertical (en mètres)
    :vartype dz_section_reference: float
    """

    def __init__(self, nom_section, section_reference, dz_section_reference=0.0):
        """

        :param nom_section: nom de la section
        :type nom_section: str
        :param section_reference: section de référence (ou source)
        :type section_reference: SectionProfil
        :param dz_section_reference: décalage vertical (en mètres)
        :type dz_section_reference: float
        """
        super().__init__(nom_section)
        check_isinstance(section_reference, SectionProfil)
        self.section_reference = section_reference
        self.dz_section_reference = dz_section_reference

    def get_as_sectionprofil(self):
        """
        Retourne une instance `SectionProfil` à partir de la section de référence

        :rtype: SectionProfil
        """
        new_section = deepcopy(self.section_reference)
        new_section.id = self.id
        new_section.xp = self.xp
        new_section.is_active = self.is_active
        new_section.xz[:, 1] += self.dz_section_reference
        new_section.comment = 'Copie de la section parent %s' % self.section_reference.id
        new_section.set_profilsection_name()  # reset ProfilSection name (avoid duplications)
        return new_section

    def get_min_z(self):
        """
        :return: cote minimale du profil en travers
        :rtype: float
        """
        section = self.get_as_sectionprofil()
        return section.xz[:, 1].min()


class SectionInterpolee(Section):
    """
    SectionInterpolee
    """
    pass


class SectionSansGeometrie(Section):
    """
    SectionSansGeometrie
    """
    pass
