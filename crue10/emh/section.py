# coding: utf-8
"""
Classes pour les sections :
    - LoiFrottement
    - LitNumerote
    - LimiteGeom
    - Section
        - SectionProfil
        - SectionIdem
        - SectionInterpolee
        - SectionSansGeometrie
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
    """Linear interpolation (equivalent to np.interp with extrapolation)

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
    Friction law (Strickler coefficient could vary with Z elevation)

    :param id: friction law identifier
    :type id: str
    :param type: friction law type
    :type type: str
    :param loi_Fk: ndarray(dtype=float, ndim=2) with Strickler coefficient varying with elevation
    :type loi_Fk: 2D-array
    :param comment: optional text explanation
    :type comment: str
    """

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
        check_isinstance(loi_values, np.ndarray)
        self.loi_Fk = loi_values

    def set_loi_constant_value(self, value):
        check_isinstance(value, float)
        self.loi_Fk[:, 1] = value

    def shift_loi_Fk_values(self, value):
        check_isinstance(value, float)
        self.loi_Fk[:, 1] += value

    def get_loi_Fk_values(self):
        return self.loi_Fk[:, 1]

    def get_loi_Fk_value(self):
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
    Lit numéroté (= intervalle entre 2 limites de lit)

    :param id: bed identifier (a key of `BED_NAMES`)
    :type id: str
    :param xt_min: first curvilinear abscissa
    :type xt_min: str
    :param xt_max: first curvilinear abscissa
    :type xt_max: str
    :param loi_frottement: friction law (take the associated default law if it is not given)
    :type loi_frottement: LoiFrottement
    """

    BED_NAMES = ['Lt_StoD', 'Lt_MajD', 'Lt_Mineur', 'Lt_MajG', 'Lt_StoG']
    LIMIT_NAMES = ['RD', 'StoD-MajD', 'MajD-Min', 'Min-MajG', 'MajG-StoG', 'RG']

    def __init__(self, nom_lit, xt_min, xt_max, loi_frottement=None):
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
        return 'Maj' in self.id or 'Min' in self.id

    @property
    def get_est_mineur(self):
        return 'Min' in self.id

    def __repr__(self):
        return 'LitNumeroté #%s (%f -> %s)' % (self.id, self.xt_min, self.xt_max)


class LimiteGeom:
    """
    Limite géométrique

    :param id: nom de la limite
    :type id: str
    :param xt: abscisse curviligne
    :type xt: float
    """

    AXE_HYDRAULIQUE = 'Et_AxeHyd'
    THALWEG = 'Et_Thalweg'

    def __init__(self, id, xt):
        check_preffix(id, 'Et_')
        self.id = id
        self.xt = xt

    def __repr__(self):
        return 'Limite #%s (%f)' % (self.id, self.xt)


class Section(ABC):
    """
    Méthode abstraite pour les sections

    :param id: section identifier
    :type id: str
    :param xp: curvilinear abscissa of section on its associated branch
    :type xp: float
    :param is_active: True if the section is connected to an active branch => used to read rcal
    :type is_active: bool
    :param CoefPond: "coefficient de pondération amont/aval de la discrétisation de la perte de charge régulière J
        entre la section et sa suivante"
    :type CoefPond: float
    :param CoefConv: "coefficient de perte de charge ponctuelle en cas de convergence entre la section et sa
        suivante"
    :type CoefConv: float
    :param CoefDiv: "coefficient de perte de charge ponctuelle en cas de divergence entre la section et sa suivante"
    :type CoefDiv: float
    :param comment: optional text explanation
    :type comment: str
    """

    def __init__(self, nom_section):
        self.id = nom_section
        self.is_active = False
        self.xp = -1
        self.CoefPond = 0.5
        self.CoefConv = 0.0
        self.CoefDiv = 0.0
        self.comment = ''

    def validate(self):
        errors = []
        if len(self.id) > 32:  # valid.nom.tooLong.short
            errors.append((self, "Le nom est trop long, il d\u00e9passe les 32 caract\u00e8res"))
        return errors

    def __repr__(self):
        return '%s #%s' % (self.__class__.__name__, self.id)


class SectionProfil(Section):
    """
    SectionProfil

    :param nom_profilsection: profil section identifier (should start with `Ps_`)
    :type nom_profilsection: str
    :param comment_profilsection: commentaire du ProfilSection
    :type comment_profilsection: str
    :param xt_axe: transversal position of hydraulic axis
    :type xt_axe: float
    :param xz: ndarray(dtype=float, ndim=2)
        Array containing series of transversal abscissa and elevation (first axis should be strictly increasing)
    :type xz: 2D-array
    :param geom_trace: polyline section trace (only between left and right bank)
    :type geom_trace: shapely.geometry.LineString
    :param largeur_fente: largeur de la fente
    :type largeur_fente: float
    :param profondeur_fente: profondeur de la fente
    :type profondeur_fente: float
    :param lits_numerotes: lits numérotés
    :type lits_numerotes: [LitNumerote]
    :param limites_geom: limites géométriques (thalweg, axe hydraulique...)
    :type limites_geom: [LimiteGeom]
    """

    def __init__(self, nom_section, nom_profilsection=None):
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
        if nom_profilsection is None:
            self.nom_profilsection = 'Ps_' + self.id[3:]
        else:
            check_preffix(nom_profilsection, 'Ps_')
            self.nom_profilsection = nom_profilsection

    @property
    def xt_axe(self):
        """Curvilinear abscissa of hydraulic axis intersection"""
        for limite in self.limites_geom:
            if limite.id == 'Et_AxeHyd':
                return limite.xt
        raise ExceptionCrue10("La limite 'Et_AxeHyd' n'existe pas pour %s" % self)

    @property
    def is_avec_fente(self):
        return self.largeur_fente is not None and self.profondeur_fente is not None

    @property
    def xz_filtered(self):
        return self.xz[np.logical_and(self.lits_numerotes[0].xt_min <= self.xz[:, 0],
                                      self.xz[:, 0] <= self.lits_numerotes[-1].xt_max), :]

    def set_xz(self, array):
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

    def set_geom_trace(self, trace):
        check_isinstance(trace, LineString)
        if trace.has_z:
            raise ExceptionCrue10("La trace de la %s ne doit pas avoir de Z !" % self)
        if not self.lits_numerotes:
            raise ExceptionCrue10('xz has to be set before (to check consistency)')
        self.geom_trace = trace

        # Display a warning if geometry is not consistent with self.xz array
        range_xt = self.xz_filtered[:, 0].max() - self.xz_filtered[:, 0].min()
        diff_xt = range_xt - self.geom_trace.length
        if abs(diff_xt) > 1e-2:
            logger.warn("Écart de longueur pour la section %s: %s" % (self, diff_xt))

    def ajouter_fente(self, largeur, profondeur):
        """Adds (or replaces if already exists) fente width and depth"""
        if largeur <= 0:
            raise ExceptionCrue10("La largeur de fente doit être strictement positive")
        if profondeur <= 0:
            raise ExceptionCrue10("La profondeur de fente doit être strictement positive")
        self.largeur_fente = largeur
        self.profondeur_fente = profondeur

    def set_lits_numerotes(self, xt_list):
        """Add directly the 5 beds from a list of 6 ordered xt values"""
        if len(xt_list) != 6:
            raise ExceptionCrue10("Il faut exactement 5 lits numérotés pour les affecter")
        if any(x > y for x, y in zip(xt_list, xt_list[1:])):
            raise ExceptionCrue10("Les valeurs de xt ne sont pas croissantes")
        self.lits_numerotes = []
        for bed_name, xt_min, xt_max in zip(LitNumerote.BED_NAMES, xt_list, xt_list[1:]):
            lit_numerote = LitNumerote(bed_name, xt_min, xt_max)
            self.lits_numerotes.append(lit_numerote)

    def ajouter_lit(self, lit_numerote):
        check_isinstance(lit_numerote, LitNumerote)
        if lit_numerote.id in self.lits_numerotes:
            raise ExceptionCrue10("Le lit numéroté `%s` est déjà présent" % lit_numerote.id)
        self.lits_numerotes.append(lit_numerote)

    def ajouter_limite_geom(self, limite_geom):
        check_isinstance(limite_geom, LimiteGeom)
        if limite_geom.id in self.limites_geom:
            raise ExceptionCrue10("La limite géométrique `%s` est déjà présente" % limite_geom.id)
        self.limites_geom.append(limite_geom)

    def interp_z(self, xt):
        return np.interp(xt, self.xz[:, 0], self.xz[:, 1])

    def interp_point(self, xt):
        """
        Interpolation et extrapolation (si en dehors des rives RD et RG) d'un point le long de la trace
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
        for lit in self.lits_numerotes:
            if lit.id == nom:
                return lit
        raise ExceptionCrue10("Aucun lit `%s` pour la %s" % (nom, self))

    def get_dernier_lit_numerote(self, nom):
        for lit in reversed(self.lits_numerotes):
            if lit.id == nom:
                return lit
        raise ExceptionCrue10("Aucun lit `%s` pour la %s" % (nom, self))

    def get_limite_geom(self, nom):
        for limite in self.limites_geom:
            if limite.id == nom:
                return limite
        raise ExceptionCrue10("La limite `%s` n'exsite pas pour la %s" % (nom, self))

    def has_xz(self):
        return self.xz is not None

    def has_trace(self):
        return self.geom_trace is not None

    def build_orthogonal_trace(self, axe_geom):
        """
        Section xp is supposed to be normalized (ie. xp is consistent with axe_geom length)
        """
        check_isinstance(axe_geom, LineString)
        xp = min(self.xp, axe_geom.length)  # in case xp is not consistant
        point = axe_geom.interpolate(xp)
        point_avant = axe_geom.interpolate(max(xp - DIFF_XP, 0.0))
        point_apres = axe_geom.interpolate(min(xp + DIFF_XP, axe_geom.length))
        distance = axe_geom.project(point_apres) - axe_geom.project(point_avant)
        u, v = (point_avant.y - point_apres.y) / distance, (point_apres.x - point_avant.x) / distance
        xt_list = [self.xz_filtered[0, 0], self.xz_filtered[-1, 0]]  # only extremities are written
        coords = [(point.x + (xt - self.xt_axe) * u, point.y + (xt - self.xt_axe) * v) for xt in xt_list]
        self.geom_trace = LineString(coords)

    def merge_consecutive_lit_numerotes(self):
        """Consective LitNumerote with the same `LitNomme` are merged in single and wider bed (LitNumerote)"""
        xt_list = [self.lits_numerotes[0].xt_min]
        for lit1, lit2 in zip(self.lits_numerotes[:-1], self.lits_numerotes[1:]):
            if lit1.id != lit2.id:
                assert lit1.xt_max == lit2.xt_min
                xt_list.append(lit1.xt_max)
        xt_list.append(self.lits_numerotes[-1].xt_max)
        self.set_lits_numerotes(xt_list)

    def get_min_z(self):
        return self.xz[:, 1].min()

    def validate(self):
        """
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

    :param section_reference: parent (= initial/reference) section
    :type section_reference: SectionProfil
    :param dz_section_reference: vertical shift (in meters)
    :type dz_section_reference: float
    """

    def __init__(self, nom_section, parent_section, dz=0.0):
        super().__init__(nom_section)
        check_isinstance(parent_section, SectionProfil)
        self.section_reference = parent_section
        self.dz_section_reference = dz

    def get_as_sectionprofil(self):
        """
        Return a SectionProfil instance from the original section
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
