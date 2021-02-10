# coding: utf-8
"""
Classes des branches des lits mineur et majeur :
    - 1 = BranchePdc
    - BrancheAvecElementsSeuil
        - 2 = BrancheSeuilTransversal
        - 4 = BrancheSeuilLateral
    - 5 = BrancheOrifice
    - 6 = BrancheStrickler
    - 12 = BrancheNiveauxAssocies
    - 14 = BrancheBarrageGenerique
    - 15 = BrancheBarrageFilEau
    - 20 = BrancheSaintVenant
"""
import abc
from builtins import super  # python2 compatibility, requires module `future`
from math import ceil
import numpy as np
from shapely.affinity import translate
from shapely.geometry import LineString, Point

from .noeud import Noeud
from .section import Section, SectionIdem, SectionInterpolee, SectionProfil, SectionSansGeometrie
from crue10.utils import check_isinstance, check_preffix, ExceptionCrue10, ExceptionCrue10GeometryNotFound, logger


# ABC below is compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})

COEFF_D = 1.0
COEFF_PDC = 1.0

DIFF_XP_TO_WARN = 20.0  # m

DEFAULT_ELTS_SEUILS = np.array([(1.0, 0.0, COEFF_D)])

DEFAULT_ELTS_SEUILS_AVEC_PDC = np.array([(1.0, 0.0, COEFF_D, COEFF_PDC)])

DEFAULT_FORMULE_PDC = 'Borda'

DEFAULT_QLIMINF = -1.0E30  # m3/s

DEFAULT_QLIMSUP = 1.0E30  # m3/s


class Branche(ABC):
    """
    Méthode abstraite pour les branches

    :param id: nom de la branche
    :type id: str
    :param type: type de branche (une clé de `Branche.TYPES`)
    :type type: int
    :param is_active: True si la branche est active
    :type is_active: bool
    :param geom: trace de la polyligne de la branche
    :type geom: LineString
    :param noeud_amont: noeud amont
    :type noeud_amont: crue10.emh.noeud.Noeud
    :param noeud_aval: noeud aval
    :type noeud_aval: crue10.emh.noeud.Noeud
    :param liste_sections_dans_branche: liste des sections
    :type liste_sections_dans_branche: [crue10.emh.section.Section]
    :param comment: optional text explanation
    :type comment: str, optional
    """

    TYPES = {
        1: 'BranchePdc',
        2: 'BrancheSeuilTransversal',
        4: 'BrancheSeuilLateral',
        5: 'BrancheOrifice',
        6: 'BrancheStrickler',
        12: 'BrancheNiveauxAssocies',
        14: 'BrancheBarrageGenerique',
        15: 'BrancheBarrageFilEau',
        20: 'BrancheSaintVenant'
    }

    # Branch types whose sections (at least 2) have a geometry (SectionProfil or SectionIdem)
    TYPES_WITH_GEOM = [2, 6, 15, 20]

    # Branch types which have a non-zero length value
    TYPES_WITH_LENGTH = [6, 20]

    # Branch types which should be located in the river bed (and not the floodplain)
    TYPES_IN_MINOR_BED = [1, 2, 20]

    def __init__(self, nom_branche, noeud_amont, noeud_aval, branch_type, is_active=True):
        """
        :param nom_branche: nom de la branche
        :type nom_branche: str
        :param noeud_amont: noeud amont
        :type noeud_amont: crue10.emh.noeud.Noeud
        :param noeud_aval: noeud aval
        :type noeud_aval: crue10.emh.noeud.Noeud
        :param is_active: True si la branche est active
        :type is_active: bool, optional
        """
        check_preffix(nom_branche, 'Br_')
        check_isinstance(noeud_amont, Noeud)
        check_isinstance(noeud_aval, Noeud)
        if branch_type not in Branche.TYPES:
            raise RuntimeError
        self.id = nom_branche
        self.type = branch_type
        self.is_active = is_active
        if noeud_amont.geom is not None and noeud_aval.geom is not None:
            self.geom = LineString([(noeud_amont.geom.x, noeud_amont.geom.y), (noeud_aval.geom.x, noeud_aval.geom.y)])
        else:
            self.geom = None
        self.noeud_amont = noeud_amont
        self.noeud_aval = noeud_aval
        self.liste_sections_dans_branche = []
        self.comment = ''

    @staticmethod
    def get_id_type_from_name(branch_type_name):
        """
        Retourne le numéro du type de branche à partir du nom du type

        :param branch_type_name: nom du type de branche
        :return: numéro de la branche
        """
        for type_id, type_name in Branche.TYPES.items():
            if type_name == branch_type_name:
                return type_id
        return None

    def get_section_amont(self):
        """
        :return: section amont
        :rtype: crue10.emh.section.Section
        """
        return self.liste_sections_dans_branche[0]

    def get_section_aval(self):
        """
        :return: section aval
        :rtype: crue10.emh.section.Section
        """
        return self.liste_sections_dans_branche[-1]

    @property
    def length(self):
        """
        :return: Longueur schématique affichée dans FC (peut différer de la longueur géométrique)
        :rtype: float
        """
        if self.type in Branche.TYPES_WITH_LENGTH:
            return self.get_section_aval().xp
        else:
            return 0.0

    @property
    def type_name(self):
        """
        :return: nom du type de branche
        :rtype: str
        """
        return Branche.TYPES[self.type]

    def has_geom(self):
        """
        :return: La branche contient des informations géométriques
        :rtype: bool
        """
        return self.type in Branche.TYPES_WITH_GEOM

    def ajouter_section_dans_branche(self, section, xp):
        """Ajouter une section à l'abscisse xp le long de la branche

        :param section: section à ajouter
        :type section: crue10.emh.section.Section
        :param xp: abscisse curviligne de la section
        :type xp: float
        """
        check_isinstance(section, Section)
        if isinstance(section, SectionInterpolee):
            if self.type != 20:
                raise ExceptionCrue10("La %s ne peut être affectée qu'à une branche Saint-Venant" % section)
        elif self.type in Branche.TYPES_WITH_GEOM:
            if not isinstance(section, SectionProfil) and not isinstance(section, SectionIdem):
                raise ExceptionCrue10("La %s ne peut porter que des SectionProfil ou SectionIdem" % self)
        else:
            if not isinstance(section, SectionSansGeometrie):
                raise ExceptionCrue10("La %s ne peut porter que des SectionSansGeometrie" % self)
        section.xp = xp
        self.liste_sections_dans_branche.append(section)

    def supprimer_section_dans_branche(self, pos_section):
        """Supprimer la section de la branche courante

        :param pos_section: index de la section (0-indexed)
        """
        del self.liste_sections_dans_branche[pos_section]

    def set_geom(self, geom):
        """Affecter la géométrie de la branche

        :param geom: polyligne correspondant à la trace de la branche
        :type geom: LineString
        """
        check_isinstance(geom, LineString)
        if geom.has_z:
            raise ExceptionCrue10("La géométrie de la %s ne doit pas avoir de Z !" % self)
        self.geom = geom

    def shift_sectionprofil_to_extremity(self):
        """
        Shift first and last SectionProfil to branch extremity
        (a constant biais is introduced by Fudaa-Crue for the graphical representation)
        """
        if self.geom is None:
            raise ExceptionCrue10GeometryNotFound(self)
        for pos in (0, -1):
            section = self.liste_sections_dans_branche[pos]
            if isinstance(section, SectionProfil):
                if pos == 0:
                    node = self.noeud_amont.geom
                else:
                    node = self.noeud_aval.geom
                if section.geom_trace is None:
                    raise ExceptionCrue10GeometryNotFound(section)
                section_point = section.geom_trace.intersection(self.geom)
                if isinstance(section_point, Point):
                    dx = node.x - section_point.x
                    dy = node.y - section_point.y
                    self.liste_sections_dans_branche[pos].set_geom_trace(
                        translate(section.geom_trace, xoff=dx, yoff=dy))

    def normalize_sections_xp(self):
        """
        Recompute section xp to correspond to geometric distance (original values are taken from drso).
        Last section xp will correspond exactly to the branch length.
        """
        xp_max = self.get_section_aval().xp
        length = self.geom.length
        if self.type in Branche.TYPES_WITH_LENGTH and abs(xp_max - length) > DIFF_XP_TO_WARN:
            logger.warn("La longueur de la branche `%s` est estimée à %.2fm (non pas %.2fm)."
                        % (self.id, length, xp_max))
        for i, section in enumerate(self.liste_sections_dans_branche):
            try:
                section.xp = section.xp * length / xp_max
            except ZeroDivisionError:
                section.xp = (i / (len(self.liste_sections_dans_branche) - 1)) * length

    def validate(self):
        errors = []
        if len(self.id) > 32:  # valid.nom.tooLong.short
            errors.append((self, "Le nom est trop long, il d\u00e9passe les 32 caract\u00e8res"))
        if len(self.liste_sections_dans_branche) < 2:  # validation.brancheMustContain2Sections
            errors.append((self, "La branche doit contenir au moins 2 sections"))
        else:
            if self.get_section_amont().xp != 0.0:  # validation.branche.firstSectionMustBeAmont
                errors.append((self, "La Section de position Amont doit avoir une abscisse nulle."))
        return errors

    def __repr__(self):
        return "Branche [%i] #%s: %s -> %s (%i sections)" % (self.type, self.id, self.noeud_amont, self.noeud_aval,
                                                             len(self.liste_sections_dans_branche))


class BranchePdC(Branche):
    """
    BranchePdC - #1

    :param loi_QPdc: loi QPdc
    :type loi_QPdc: 2D-array
    :param comment_loi: commentaire loi
    :type comment_loi: str
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 1, is_active)
        self.loi_QPdc = np.array([(-15000.0, 0.0)])
        self.comment_loi = ''

    @property
    def name_loi_LoiQPdc(self):
        return 'LoiQPdc_%s' % self.id[3:]


class BrancheAvecElementsSeuil(Branche):
    """
    Branche avec des éléments de seuil

    :param formule_pertes_de_charge: 'Borda' or 'Divergent'
    :type formule_pertes_de_charge: str
    :param liste_elements_seuil: ndarray(dtype=float, ndim=2 with 4 columns: Largeur, Zseuil, CoefD, CoefPdc)
    :type liste_elements_seuil: 2D-array
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, type, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, type, is_active)
        self.formule_pertes_de_charge = DEFAULT_FORMULE_PDC
        self.liste_elements_seuil = None
        self.set_liste_elements_seuil(DEFAULT_ELTS_SEUILS_AVEC_PDC)

    def set_liste_elements_seuil(self, elements_seuil):
        """
        :param elements_seuil: array avec 4 valeurs pour l'axe n°1 (Largeur, Zseuil, CoefD, CoefPdc)
        :type elements_seuil: 2D-array
        """
        if elements_seuil.shape[0] < 1:
            raise ExceptionCrue10("Il faut au moins 1 valeur pour axis=0")
        if elements_seuil.shape[1] != 4:
            raise ExceptionCrue10("Il faut exactement 4 valeurs pour axis=1")
        self.liste_elements_seuil = elements_seuil

    def set_liste_elements_seuil_avec_coeff_par_defaut(self, elements_seuil):
        """
        :param elements_seuil: 2D array with 2 values for axis=1 (Largeur, Zseuil)
        """
        if elements_seuil.shape[0] < 1:
            raise ExceptionCrue10("Il faut au moins 1 valeur pour axis=0")
        if elements_seuil.shape[1] != 2:
            raise ExceptionCrue10("Il faut exactement 2 valeurs pour axis=1")
        nb_elem = elements_seuil.shape[0]
        new_array = np.column_stack((elements_seuil, np.ones(nb_elem) * COEFF_D, np.ones(nb_elem) * COEFF_PDC))
        self.set_liste_elements_seuil(new_array)

    def decouper_seuil_elem(self, largeur, delta_z):
        """
        Découper les éléments de seuil trop longs
        :param largeur: largeur maximale des éléments de seuil
        :type largeur: float
        :param delta_z: page dans laquelle rediscrétiser les éléments de seuil
        :type delta_z: float
        """
        new_elements_seuil = []
        for larg, z_seuil, coeff_d, coeff_pdc in self.liste_elements_seuil:
            if larg < largeur:
                new_elements_seuil.append([larg, z_seuil, coeff_d, coeff_pdc])
            else:
                nb_decoupages = ceil(larg/largeur)
                new_largeur = larg/nb_decoupages
                for new_z_seuil in np.linspace(start=z_seuil - delta_z/2, stop=z_seuil + delta_z/2, num=nb_decoupages):
                    new_elements_seuil.append([new_largeur, new_z_seuil, coeff_d, coeff_pdc])
        self.set_liste_elements_seuil(np.array(new_elements_seuil))

    def get_min_z(self):
        return self.liste_elements_seuil[:, 1].min()


class BrancheSeuilTransversal(BrancheAvecElementsSeuil):
    """
    BrancheSeuilTransversal - #2
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 2, is_active)


class BrancheSeuilLateral(BrancheAvecElementsSeuil):
    """
    BrancheSeuilLateral - #4
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 4, is_active)


class BrancheOrifice(Branche):
    """
    BrancheOrifice - #5

    :param CoefCtrLim: "Coefficient maximum de contraction de la veine submergée"
    :type CoefCtrLim: float
    :param Largeur: "Largeur"
    :type Largeur: float
    :param Zseuil: "Cote du radier du clapet"
    :type Zseuil: float
    :param CoefD: "Coefficient de débitance"
    :type CoefD: float
    :param Haut: "Hauteur du clapet à pleine ouverture"
    :type Haut: float
    :param SensOrifice: "Sens de l'écoulement"
    :type SensOrifice: str
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 5, is_active)
        self.CoefCtrLim = 0.65
        self.Largeur = 1.0
        self.Zseuil = 0.0
        self.Haut = 1.0
        self.CoefD = 1.0
        self.SensOrifice = 'Bidirect'

    def get_min_z(self):
        return self.Zseuil


class BrancheStrickler(Branche):
    """
    BrancheStrickler - #6
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 6, is_active)


class BrancheNiveauxAssocies(Branche):
    """
    BrancheNiveauxAssocies - #12

    :param comment: commentaire
    :type comment: str
    :param QLimInf: "Débit  minimum admis dans la branche"
    :type QLimInf: float
    :param QLimSup: "Débit maximum admis dans la branche"
    :type QLimSup: float
    :param loi_ZavZam: ndarray(dtype=float, ndim=2 with 2 columns)
    :type loi_ZavZam: 2D-array
    :param comment_loi: commentaire loi
    :type comment_loi: str
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 12, is_active)
        self.QLimInf = DEFAULT_QLIMINF
        self.QLimSup = DEFAULT_QLIMSUP
        self.loi_ZavZam = np.array([(-15.0, -15.0)])
        self.comment_loi = ''

    @property
    def name_loi_ZavZam(self):
        return 'LoiZavZam_%s' % self.id[3:]


class BrancheBarrageGenerique(Branche):
    """
    BrancheBarrageGenerique - #14

    :param section_pilote: section de pilotage
    :type section_pilote: crue10.emh.section.Section
    :param QLimInf: "Débit  minimum admis dans la branche"
    :type QLimInf: float
    :param QLimSup: "Débit maximum admis dans la branche"
    :type QLimSup: float
    :param loi_QDz: ndarray(dtype=float, ndim=2 with 2 columns)
    :type loi_QDz: 2D-array
    :param loi_QpilZam: ndarray(dtype=float, ndim=2 with 2 columns)
    :type loi_QpilZam: 2D-array
    :param comment_denoye: commentaire loi dénoyée
    :type comment_denoye: str
    :param comment_noye: commentaire loi noyée
    :type comment_noye: str
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 14, is_active)
        self.section_pilote = None
        self.QLimInf = DEFAULT_QLIMINF
        self.QLimSup = DEFAULT_QLIMSUP
        self.loi_QDz = np.array([(-15000.0, -1.0E30)])
        self.loi_QpilZam = np.array([(0.0, -15.0)])
        self.comment_denoye = ''
        self.comment_noye = ''

    @property
    def name_loi_QDz(self):
        return 'LoiQDz_%s' % self.id[3:]

    @property
    def name_loi_QpilZam(self):
        return 'LoiQpilZam_%s' % self.id[3:]

    def validate(self):
        errors = super().validate()
        if self.section_pilote is None:  # validation.branche.mustContainSectionPilote
            errors.append((self, "La branche doit contenir une Section pilote."))
        return errors


class BrancheBarrageFilEau(Branche):
    """
    BrancheBarrageFilEau - #15

    :param section_pilote: section de pilotage
    :type section_pilote: crue10.emh.section.Section
    :param QLimInf: "Débit  minimum admis dans la branche"
    :type QLimInf: float
    :param QLimSup: "Débit maximum admis dans la branche"
    :type QLimSup: float
    :param loi_QZam: ndarray(dtype=float, ndim=2 with 2 columns)
    :type loi_QZam: 2D-array
    :param liste_elements_seuil: ndarray(dtype=float, ndim=2 with 3 columns: Largeur, Zseuil, CoefD)
    :type liste_elements_seuil: 2D-array
    :param comment_denoye: commentaire loi dénoyée
    :type comment_denoye: str
    """
    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 15, is_active)
        self.section_pilote = None
        self.QLimInf = DEFAULT_QLIMINF
        self.QLimSup = DEFAULT_QLIMSUP
        self.loi_QZam = np.array([(0.0, -15.0)])
        self.liste_elements_seuil = DEFAULT_ELTS_SEUILS
        self.comment_denoye = ''

    @property
    def name_loi_QZam(self):
        return 'LoiQpilZam_%s' % self.id[3:]

    def set_loi_QZam(self, loi_QZam):
        """Affecte la loi QZam

        :param loi_QZam: loi QZam
        :type loi_QZam: 2D-array
        """
        if loi_QZam.shape[0] < 1:
            raise ExceptionCrue10("Il faut au moins 1 valeur pour axis=0")
        if loi_QZam.shape[1] != 2:
            raise ExceptionCrue10("Il faut exactement 2 valeurs pour axis=1")
        if any(x >= y for x, y in zip(loi_QZam[:, 0], loi_QZam[1:, 0])):
            raise ExceptionCrue10("Les valeurs de Q ne sont pas strictement croissantes")
        self.loi_QZam = loi_QZam

    def validate(self):
        errors = super().validate()
        if self.section_pilote is None:  # validation.branche.mustContainSectionPilote
            errors.append((self, "La branche doit contenir une Section pilote."))
        return errors


class BrancheSaintVenant(Branche):
    """
    BrancheSaintVenant - #20

    :param CoefSinuo: "coefficient de sinuosité de la branche, rapport des longueurs des axes hydrauliques
         du lit mineur et du lit majeur"
    :type CoefSinuo: float
    :param CoefBeta: "coefficient de modulation global à la branche du coefficient de Boussinesq,
         afin de tenir compte de la forme du profil des vitesses sur le calcul de la QdM de l'écoulement"
    :type CoefBeta: float
    :param CoefRuis: "coefficient modulation du débit linéique de ruissellement"
    :type CoefRuis: float
    :param CoefRuisQdm: "coefficient de prise en compte du débit de ruissellement dans la QdM de l'écoulement"
    :type CoefRuisQdm: float
    """

    def __init__(self, nom_branche, noeud_amont, noeud_aval, is_active=True):
        super().__init__(nom_branche, noeud_amont, noeud_aval, 20, is_active)
        self.CoefSinuo = 1.0
        self.CoefBeta = 1.0
        self.CoefRuis = 0.0
        self.CoefRuisQdm = 0.0

    def validate(self):
        errors = super().validate()
        for section1, section2 in zip(self.liste_sections_dans_branche, self.liste_sections_dans_branche[1:]):
            if section1.xp >= section2.xp:
                errors.append((self, "Les abscisses ne sont pas strictement croissantes entre %s et %s"
                               % (section1.id, section2.id)))
        return errors


BRANCHE_CLASSES = [BranchePdC, BrancheSeuilTransversal, BrancheSeuilLateral, BrancheOrifice, BrancheStrickler,
                   BrancheNiveauxAssocies, BrancheBarrageGenerique, BrancheBarrageFilEau, BrancheSaintVenant]
