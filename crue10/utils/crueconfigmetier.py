# coding: utf-8

# Imports
import os.path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from enum import IntEnum                        # Python >= 3.7
import math
# from future.utils import with_metaclass         # Python2 compatibility
# from crue10.utils.design_patterns import Singleton
from crue10.utils import DATA_FOLDER_ABSPATH, ExceptionCrue10, PREFIX

"""
Classe statique, pour exploiter le CrueConfigMetier.
Si on souhaite forcer son unicité au niveau de l'application, utiliser la métaclasse Singleton. 
"""

# Variables de module; certaines sont déclarées ici, d'autres plus bas, mais toutes indiquées pour mémoire
CCM_FILE = os.path.normpath(os.path.join(DATA_FOLDER_ABSPATH, 'CrueConfigMetier.xml'))  #: Chemin vers le fichier CCM
# CCM = None                                                                            #: Classe statique CCM


class CrueConfigMetierTypeNum:
    """ Élément de CrueConfigMetier de type TypeNumerique.
    """
    # Variables de classe
    TYPE_NUMERIQUE = {                              #: Association entre types numériques CCM et types Python
        'Tnu_Entier': int, 'Tnu_Reel': float, 'Tnu_Date': datetime, 'Tnu_Duree': timedelta}
    FMT_DAT = '%Y-%m-%dT%H:%M:%S.%f'                #: Format par défaut des dates
    EPOCH_DAT = datetime(1970, 1, 1)                #: Origine des dates, convention Unix (1er janv 1970)

    def __init__(self, nom, src_xml):
        """ Construire l'instance de classe.
        :param nom: nom de la nature de variable
        :type nom: str
        :param src_xml: sous-arbre XML de CCM pour la description de la nature de variable
        :type src_xml: ElementTree
        """
        self.nom = nom                              # Nom de la nature de variable
        self.typ = self.TYPE_NUMERIQUE.get(nom)     # Type numérique Python de la variable
        if self.typ is None:
            raise ExceptionCrue10("Erreur type numérique `%s` inconnu" % nom)
        for itm in src_xml:
            self.infini = self.convert(itm.text)    # Valeur numérique représentant l'infini

    def __repr__(self):
        """ Renvoyer le type numérique sous-jacent, par appel direct de l'instance.
        """
        return self.typ

    def get_fmt(self, pre):
        """ Renvoyer le format Python de représentation du nombre selon son type et la précision demandée.
        :param pre: précision demandée TODO voir s'il est nécessaire de gérer les Tnu_Date et Tnu_Duree (pre inutile) ?
        :type pre: int
        :return: format Python
        :rtype: str
        """
        fmt = ''
        if self.typ == int:
            fmt = "%id" % (pre + 1)
        elif self.typ == float:
            fmt = ".%if" % abs(pre) if (pre < 0) else "%i.0f" % (pre + 1)
        elif self.typ == datetime:
            fmt = '%Y-%m-%d %H:%M:%S'
        return fmt

    def convert(self, val):
        """ Convertir (cast) la valeur val dans le type numérique.
        :param val: valeur textuelle à convertir, incluant les infinis
        :type val: str
        :return: valeur convertie
        :rtype: type numérique visé
        """
        if val == '-Infini':
            return -self.infini
        elif val == '+Infini':
            return +self.infini
        else:
            if ':' in val:
                # Cas d'une date
                dat = datetime.strptime(val, self.FMT_DAT)
                val = (dat - self.EPOCH_DAT).total_seconds()  # Écart avec l'Epoch de référence
            return self.typ(float(val)) if (val is not None) else val

    def txt(self, val, fmt):
        """ Convertir une valeur en chaine formatée selon son type, en gérant les infinis.
        :param val: valeur numérique à convertir
        :type val: type numérique de la variable
        :param fmt: format à appliquer
        :type fmt: str
        :return: chaine formatée
        :rtype: str
        """
        if val <= -self.infini:
            return '-Infini'
        if val >= self.infini:
            return '+Infini'
        str_fmt = "{{val:{fmt}}}".format(fmt=fmt) if fmt != '' else "{val}"
        return str_fmt.format(val=val)


class CrueConfigMetierType:
    """ Élément de CrueConfigMetier, interface pour CrueConfigMetierEnum et CrueConfigMetierNature.
    """
    def __init__(self, nom):
        self._nom = nom                         # Nom de l'instance
        self._fmt = ''                          # Format Python de représentation
        self._unt = ''                          # Unité de représentation

    @property
    def nom(self):
        return self._nom

    @property
    def fmt(self):
        return self._fmt

    @property
    def unt(self):
        return self._unt

    def convert(self, val):
        """ Convertir une valeur en valeur du type sous-jacent. À spécialiser.
        """
        raise NotImplementedError

    def txt(self, val, add_unt=False):
        """ Convertir une valeur en chaine formatée. À spécialiser.
        """
        raise NotImplementedError

    def txt_eps(self, val):
        """ Formater une valeur selon son epsilon de comparaison. À spécialiser.
        """
        raise NotImplementedError

    def valider(self, nom, val, vld_min, vld_min_stc, vld_max, vld_max_stc, nrm_min, nrm_min_stc, nrm_max, nrm_max_stc):
        """ Tester la normalité et la validité de la variable, en fonction de sa valeur. À spécialiser.
        """
        raise NotImplementedError

    def is_egal(self, val_a, val_b):
        """ Vérifier l'égalité de deux valeurs. À spécialiser.
        """
        raise NotImplementedError


class CrueConfigMetierEnum(CrueConfigMetierType):
    """ Élément de CrueConfigMetier de type Enum.
    Cette classe agit comme un wrapper autour de IntEnum (Enum avec des valeurs int), mais ajoute un nom.
    """
    def __init__(self, nom, src_xml):
        """ Construire l'instance de classe.
        :param nom: nom de l'Enum
        :type nom: str
        :param src_xml: sous-arbre XML de CCM pour la description de l'Enum
        :type src_xml: ElementTree
        """
        super().__init__(nom)                   # Instancier la classe mère
        dic_nom_int = {}                        # Dictionnaire {clé: valeur_int} pour l'Enum
        for itm in src_xml:
            dic_nom_int[itm.text] = int(itm.get('Id'))
        self._enum = IntEnum(nom, dic_nom_int)  # Enum sous-jacente

    def __repr__(self):
        """ Renvoyer l'Enum sous-jacente, par appel direct de l'instance.
        """
        return self._enum

    def __cmp__(self, other):
        """ Renvoyer l'Enum sous-jacente pour les comparaisons (==, !=, >, >=, <, <=).
        """
        return self._enum.__cmp__(other)

    def __getitem__(self, key):
        """ Renvoyer l'Enum sous-jacente pour les appels 'self[key]'.
        """
        return self._enum[key]

    def __getattr__(self, name):
        """ Renvoyer l'Enum sous-jacente pour les appels 'self.name'.
        """
        return self._enum[name]

    def convert(self, val):
        """ Convertir une valeur en Enum sous-jacente.
        :param val: valeur textuelle à convertir
        :type val: str
        :return: valeur d'Enum associée
        :rtype: Enum
        """
        return self._enum[val]

    def nat(self):
        """ Renvoyer la nature: Enum sous-jacente.
        :return: nature
        :rtype: CrueConfigMetierNature
        """
        return self._enum

    @property
    def eps(self):
        """ Renvoyer l'epsilon de comparaison: aucune pour une Enum.
        :return: epsilon de comparaison
        :rtype: float
        """
        return 0

    def txt(self, val, add_unt=False):
        """ Convertir une valeur en chaine formatée avec le code de l'Enum et la valeur associée.
        :param val: valeur textuelle à convertir
        :type val: str
        :param add_unt: ajouter l'unité, sans effet pour une Enum
        :type add_unt: bool
        :return: chaine formatée
        :rtype: str
        """
        val_enum = self.convert(val)
        return "{0}({1})".format(val_enum.name, val_enum.value)

    def txt_eps(self, val):
        """ Formater une valeur en chaine formatée.
        :param val: valeur à formater
        :vartype val: str
        :return: valeur formatée
        :rtype: str
        """
        return self.txt(val, add_unt=False)

    def valider(self, nom, val, vld_min=None, vld_min_stc=None, vld_max=None, vld_max_stc=None,
        nrm_min=None, nrm_min_stc=None, nrm_max=None, nrm_max_stc=None):
        """ Tester la normalité et la validité de la variable: aucunes pour une Enum.
        :param nom: nom de l'Enum à tester
        :vartype nom: str
        :param val: valeur à analyser
        :vartype val: str
        :return: tuple (True si valeur normale et valide ou False sinon; chaîne descriptive si False)
        :rtype: (bool, str)
        """
        try:
            val_enum = self.convert(val)
            return True, ''
        except ValueError:
            return False, f"{val} invalide pour {self.nom}"

    def is_egal(self, val_a, val_b):
        """ Vérifier l'égalité de deux valeurs.
        :param val_a: première valeur
        :type val_a: str
        :param val_b: seconde valeur
        :type val_a: str
        :return: résultat de l'égalité
        :rtype: bool
        """
        return self.convert(val_a) == self.convert(val_b)


class CrueConfigMetierNature(CrueConfigMetierType):
    """ Élément de CrueConfigMetier de type Nature de variable.
    """
    def __init__(self, nom, src_xml):
        """ Construire l'instance de classe.
        :param nom: nom de la nature
        :type nom: str
        :param src_xml: sous-arbre XML de CCM pour la description de la nature
        :type src_xml: ElementTree
        """
        # Déclarer et initialiser les variables membres
        super().__init__(nom)                   # Instancier la classe mère
        self.typ = self._load_typ(src_xml)      # Type numérique
        self._unt = self._load_unt(src_xml)     # Unité
        self.eps = self._load_eps(src_xml)              # Epsilon de comparaison
        self.eps_prt = self._load_eps_prt(src_xml)      # Epsilon de présentation
        self._fmt = self._get_fmt_eps(self.eps)         # Format de présentation
        self._fmt_eps = self._get_fmt_eps(self.eps_prt) # Format de comparaison (nombre de chiffres représentatifs)

    def _load_typ(self, src_xml):
        """ Extraire le type numérique associé à la nature.
        :param src_xml: sous-arbre XML de CCM
        :type src_xml: ElementTree
        :return: type numérique
        :rtype: CrueConfigMetierTypeNum
        """
        typ = '?'
        try:
            typ = src_xml.find(PREFIX + 'TypeNumerique').get('NomRef')
            return CCM.typ_num[typ]
        except AttributeError as e:
            raise ExceptionCrue10("Erreur type numérique `%s` incompatible pour nature `%s`:\n%s" % (typ, self.nom, e))

    def _load_eps(self, src_xml):
        """ Extraire l'epsilon de comparaison associé à la nature.
        :param src_xml: sous-arbre XML de CCM
        :type src_xml: ElementTree
        :return: valeur de l'epsilon de comparaison
        :rtype: int|float|datetime|timedelta
        """
        eps, str_eps = None, None
        try:
            str_eps = src_xml.find(PREFIX + 'EpsilonComparaison').text
            eps = self.typ.convert(str_eps)
        except AttributeError:
            pass
        return eps if (eps is not None) else 0.0

    def _load_eps_prt(self, src_xml):
        """ Extraire l'epsilon de présentation associé à la nature.
        :param src_xml: sous-arbre XML de CCM
        :type src_xml: ElementTree
        :return: valeur de l'epsilon de présentation
        :rtype: int|float|datetime|timedelta
        """
        eps, str_eps = None, None
        try:
            str_eps = src_xml.find(PREFIX + 'EpsilonPresentation').text
            eps = self.typ.convert(str_eps)
        except AttributeError:
            pass
        return eps if (eps is not None) else 0.0

    def _load_unt(self, src_xml):
        """ Extraire l'unité associée à la nature.
        :param src_xml: sous-arbre XML de CCM
        :type src_xml: ElementTree
        :return: unité
        :rtype: str
        """
        unt = None
        try:
            unt = src_xml.find(PREFIX + 'Unite').text
        except AttributeError:
            pass
        return unt if (unt is not None) else ''

    def _get_fmt_eps(self, eps):
        """ Renvoyer le format (nombre de chiffres représentatifs) associé à la nature.
        :param eps: valeur numérique de l'epsilon
        :type eps: int|float
        :return: format de comparaison Python
        :rtype: str
        """
        fmt = ''
        try:
            pre = math.floor(math.log10(eps))  # Précision, pour déduire le nombre de chiffres à afficher
        except ArithmeticError:
            pre = 1
        fmt = self.typ.get_fmt(pre)
        return fmt

    def __getitem__(self, val):
        """ Convertir une valeur en valeur du type numérique sous-jacent; appel par 'self[val]'.
        :param val: valeur textuelle à convertir
        :type val: str
        :return: valeur numérique associée
        :rtype: int|float|datetime|timedelta
        """
        return self.typ.convert(val)

    def convert(self, val):
        """ Convertir une valeur en valeur du type numérique sous-jacent.
        :param val: valeur textuelle à convertir
        :type val: str
        :return: valeur numérique associée
        :rtype: int|float|datetime|timedelta
        """
        return self.typ.convert(val)

    def txt(self, val, add_unt=True):
        """ Convertir une valeur numérique en chaine formatée.
        :param val: valeur numérique à convertir
        :type val: int
        :param add_unt: ajouter l'unité
        :type add_unt: bool
        :return: chaine formatée
        :rtype: str
        """
        txt = self.typ.txt(val, self.fmt)
        txt += (' ' + self.unt) if (add_unt and self.unt != '') else ''
        return txt

    def txt_eps(self, val):
        """ Formater une valeur selon son epsilon de comparaison (chaîne avec tous les chiffres significatifs).
        :param val: valeur à formater
        :vartype val: int|float|datetime|timedelta
        :return: valeur formatée
        :rtype: str
        """
        return self.typ.txt(val, self._fmt_eps)

    def valider(self, nom, val, vld_min, vld_min_stc, vld_max, vld_max_stc, nrm_min, nrm_min_stc, nrm_max, nrm_max_stc):
        """ Tester la normalité et la validité de la variable, en fonction de sa valeur.
        :param nom: nom de la variable à tester
        :vartype nom: str
        :param val: valeur à analyser
        :vartype val: int|float|datetime|timedelta
        :param vld_min: minimum de la plage de validité
        :param vld_min_stc: minimum strict
        :param vld_max: maximum de la plage de validité
        :param vld_max_stc: maximum strict
        :param nrm_min: minimum de la plage de normalité
        :param nrm_min_stc: minimum strict
        :param nrm_max: maximum de la plage de normalité
        :param nrm_max_stc: maximum strict
        :return: tuple (True si valeur normale et valide ou False sinon; chaîne descriptive si False)
        :rtype: (bool, str)
        """
        # Définir une inner function utilitaire: test élémentaire pour une borne min ou max
        def valider_elem(_val, brn, brn_stc, is_max=True):
            if is_max:
                # Tester le max
                is_vld = not (_val >= brn if (brn_stc is True) else _val > brn)
                msg_elem = self.txt(brn, add_unt=False) + ('[' if (brn_stc is True) else ']')
            else:
                # Tester le min
                is_vld = not (_val <= brn if (brn_stc is True) else _val < brn)
                msg_elem = (']' if (brn_stc is True) else '[') + self.txt(brn, add_unt=False)
            return is_vld, msg_elem

        # Tester la validité
        str_val = self.txt(val, add_unt=True)
        is_vld_min, msg_min = valider_elem(val, vld_min, vld_min_stc, is_max=False)
        is_vld_max, msg_max = valider_elem(val, vld_max, vld_max_stc, is_max=True)
        vld = is_vld_min and is_vld_max
        if not vld:
            msg = "{}={} est invalide: hors de l'intervale {};{}".format(nom, str_val, msg_min, msg_max)
            return vld, msg

        # Tester la normalité
        is_nrm_min, msg_min = valider_elem(val, nrm_min, nrm_min_stc, is_max=False)
        is_nrm_max, msg_max = valider_elem(val, nrm_max, nrm_max_stc, is_max=True)
        nrm = is_nrm_min and is_nrm_max
        if not nrm:
            msg = "{}={} est anormale: hors de l'intervale {};{}".format(nom, str_val, msg_min, msg_max)
            return nrm, msg

        # Valeur valide et normale
        return True, ''

    def is_egal(self, val_a, val_b):
        """ Vérifier l'égalité de deux valeurs à l'epsilon de comparaison près.
        :param val_a: première valeur
        :type val_a: int|float|datetime|timedelta
        :param val_b: seconde valeur
        :type val_a: int|float|datetime|timedelta
        :return: résultat de l'égalité
        :rtype: bool
        """
        return abs(val_a - val_b) <= self.eps


class CrueConfigMetierVariable:
    """ Classe commune pour les Constantes et les Variables.
    """
    def __init__(self, nom, src_xml):
        """ Construire l'instance de classe.
        :param nom: nom de la constante ou de la variable
        :type nom: str
        :param src_xml: sous-arbre XML de CCM pour la description d'élément
        :type src_xml: ElementTree
        """
        self.nom = nom                              # Nom de la constante ou de la variable
        self._enum = self._load_typ_enum(src_xml)   # Type de l'Enum si applicable
        self._nat = self._load_nat(src_xml)         # Nature si applicable
        self.dft = self._load_dft(src_xml)          # Valeur ou valeur par défaut
        self.vld_min, self.vld_min_stc = self._load_borne(src_xml, typ='MinValidite')   # Minimum plage de validité
        self.vld_max, self.vld_max_stc = self._load_borne(src_xml, typ='MaxValidite')   # Maximum plage de validité
        self.nrm_min, self.nrm_min_stc = self._load_borne(src_xml, typ='MinNormalite')  # Minimum plage de normalité
        self.nrm_max, self.nrm_max_stc = self._load_borne(src_xml, typ='MaxNormalite')  # Maximum plage de normalité

    def _load_typ_enum(self, src_xml):
        """ Extraire le type de l'Enum, si applicable.
        :param src_xml: sous-arbre XML de CCM
        :type src_xml: ElementTree
        :return: type de l'Enum
        :rtype: CrueConfigMetierEnum
        """
        enum = None
        try:
            enum = src_xml.find(PREFIX + 'TypeEnum').get('NomRef')
        except AttributeError:
            pass
        return CCM.enum[enum] if (enum is not None) else None

    def _load_nat(self, src_xml):
        """ Extraire la nature, si applicable.
        :param src_xml: sous-arbre XML de CCM
        :type src_xml: ElementTree
        :return: nature
        :rtype: CrueConfigMetierNature
        """
        nat = None
        try:
            nat = src_xml.find(PREFIX + 'Nature').get('NomRef')
        except AttributeError:
            pass
        return CCM.nature[nat] if (nat is not None) else None

    def _load_dft(self, src_xml):
        """ Extraire la valeur par défaut, la valeur, ou le vecteur valeur, selon le cas.
        :param src_xml: sous-arbre XML de CCM
        :type src_xml: ElementTree
        :return: valeur ou vecteur de valeurs
        :rtype: any
        """
        # Définir une inner function utilitaire: analyser un élément XML
        def get_dft(str_find, nat=None):
            str_dft = None
            try:
                str_dft = src_xml.find(PREFIX + str_find).text  # Texte dans la balise XML
            except AttributeError:
                pass
            try:
                return nat.convert(str_dft) if (str_dft is not None and nat is not None) else str_dft
            except KeyError:
                raise ExceptionCrue10("Erreur valeur par défaut `%s` incompatible pour `%s`" % (str_dft, self.nom))

        # Rechercher à différents emplacements
        dft = get_dft(str_find='EnumValeurDefaut', nat=self.nat)                        # Variable de type Enum
        dft = get_dft(str_find='ValeurDefaut', nat=self.nat) if dft is None else dft    # Variable autres types
        dft = get_dft(str_find='Valeur', nat=self.nat) if dft is None else dft          # Constante simple
        dft = get_dft(str_find='ValeurVecteur', nat=None) if dft is None else dft       # Constante vecteur
        return dft

    def _load_borne(self, src_xml, typ):
        """ Extraire la borne (min/max) de validité/normalité pour la variable.
        :param src_xml: sous-arbre XML de CCM
        :type src_xml: ElementTree
        :param typ: balise XML à analyser
        :type typ: str
        :return: valeur de la borne ou None; True si inégalité stricte ou False si la borne est incluse
        :rtype: (int|float|datetime|timedelta|None, bool)
        """
        brn, brn_stc = None, False
        try:
            str_brn = src_xml.find(PREFIX + typ).text   # Texte dans la balise XML
            brn = self.nat.convert(str_brn) if (str_brn is not None and self.nat is not None) else str_brn
            brn_stc = (src_xml.find(PREFIX + typ).get('Strict') == 'true')
        except AttributeError:
            pass
        return brn, brn_stc

    @property
    def nat(self):
        """ Renvoyer la nature de la constante ou de la variable.
        :return: nature
        :rtype: CrueConfigMetierNature
        """
        return self._nat if (self._enum is None) else self._enum

    @property
    def unt(self):
        """ Renvoyer l'unité de la constante ou de la variable.
        :return: unité
        :rtype: str
        """
        return self.nat.unt

    @property
    def eps(self):
        """ Renvoyer l'epsilon de comparaison de la constante ou de la variable.
        :return: epsilon de comparaison
        :rtype: float
        """
        return self._nat.eps if (self._enum is None) else 0

    def txt(self, val, add_unt=True):
        """ Formater une valeur selon sa variable ou sa nature et renvoyer une chaîne.
        :param val: valeur à formater
        :vartype val: int|float|datetime|timedelta
        :param add_unt: True pour ajouter son unité ou False sinon
        :vartype add_unt: bool
        :return: valeur formatée
        :rtype: str
        """
        return self.nat.txt(val, add_unt)

    def txt_eps(self, val):
        """ Formater une valeur selon son epsilon de comparaison (chaîne avec tous les chiffres significatifs).
        :param val: valeur à formater
        :vartype val: int|float|datetime|timedelta
        :return: valeur formatée
        :rtype: str
        """
        return self.nat.txt_eps(val)

    def valider(self, val):
        """ Tester la normalité et la validité de la variable, en fonction de sa valeur.
        :param val: valeur à analyser
        :vartype val: int|float|datetime|timedelta
        :return: tuple (True si valeur normale et valide ou False sinon; chaîne descriptive si False)
        :rtype: (bool, str)
        """
        return self.nat.valider(self.nom, val, self.vld_min, self.vld_min_stc, self.vld_max, self.vld_max_stc,
            self.nrm_min, self.nrm_min_stc, self.nrm_max, self.nrm_max_stc)

    def is_egal(self, val_a, val_b):
        """ Vérifier l'égalité de deux valeurs à l'epsilon de comparaison près.
        :param val_a: première valeur
        :type val_a: int|float|datetime|timedelta
        :param val_b: seconde valeur
        :type val_a: int|float|datetime|timedelta
        :return: résultat de l'égalité
        :rtype: bool
        """
        return self.nat.is_egal(val_a, val_b)


class CrueConfigMetier:  # CrueConfigMetier(with_metaclass(Singleton)) si on exclut d'avoir des CCM sur différents cœurs
    """ Classe lectrice du fichier CrueConfigMetier.
    """
    def __init__(self):
        """ Construire l'instance de classe.
        """
        self.ccm_path = None
        self.ccm_root = None
        self.dic_typ_num = {}
        self.dic_enum = {}
        self.dic_nature = {}
        self.dic_constante = {}
        self.dic_variable = {}
        self.dic_loi = {}

    def load(self, ccm_path=CCM_FILE):
        """ Charger à partir du fichier.
        :param ccm_path: nom long du fichier
        :type ccm_path: str
        """
        try:
            self.ccm_path = ccm_path
            self.ccm_root = ET.parse(ccm_path).getroot()
            self.dic_typ_num = self._read_typ_num()
            self.dic_enum = self._read_enum()
            self.dic_nature = self._read_nature()
            self.dic_constante = self._read_constante()
            self.dic_variable = self._read_variable()
        except ET.ParseError as e:
            raise ExceptionCrue10("Erreur syntaxe XML dans `%s`:\n%s" % (self.ccm_path, e))

    def _read_typ_num(self):
        """ Lire les TypeNumeriques.
        :return: dictionnaire des types numériques
        :rtype: {nom: CrueConfigMetierTypeNum}
        """
        dic_typ_num = {}
        for itm in self.ccm_root.find(PREFIX + 'TypeNumeriques'):
            nom = itm.get('Nom')
            dic_typ_num[nom] = CrueConfigMetierTypeNum(nom=nom, src_xml=itm)
        return dic_typ_num

    def _read_enum(self):
        """ Lire les Enum.
        :return: dictionnaire des Enum
        :rtype: {nom: CrueConfigMetierEnum}
        """
        dic_enum = {}
        for itm in self.ccm_root.find(PREFIX + 'TypeEnums'):
            nom = itm.get('Nom')
            dic_enum[nom] = CrueConfigMetierEnum(nom=nom, src_xml=itm)
        return dic_enum

    def _read_nature(self):
        """ Lire les Natures.
        :return: dictionnaire des natures
        :rtype: {nom: CrueConfigMetierNature}
        """
        dic_nature = {}
        for itm in self.ccm_root.find(PREFIX + 'Natures'):
            nom = itm.get('Nom')
            dic_nature[nom] = CrueConfigMetierNature(nom=nom, src_xml=itm)
        return dic_nature

    def _read_constante(self):
        """ Lire les Constantes.
        :return: dictionnaire des constantes
        :rtype: {nom: CrueConfigMetierVariable}
        """
        dic_constante = {}
        for itm in self.ccm_root.find(PREFIX + 'Constantes'):
            nom = itm.get('Nom')
            dic_constante[nom] = CrueConfigMetierVariable(nom=nom, src_xml=itm)
        return dic_constante

    def _read_variable(self):
        """ Lire les Variables.
        :return: dictionnaire des variables
        :rtype: {nom: CrueConfigMetierVariable}
        """
        dic_variable = {}
        for itm in self.ccm_root.find(PREFIX + 'Variables'):
            nom = itm.get('Nom')
            dic_variable[nom] = CrueConfigMetierVariable(nom=nom, src_xml=itm)
        return dic_variable

    @property
    def typ_num(self):
        return self.dic_typ_num

    @property
    def enum(self):
        return self.dic_enum

    @property
    def nature(self):
        return self.dic_nature

    @property
    def constante(self):
        return self.dic_constante

    @property
    def variable(self):
        return self.dic_variable


# Variables de module; certaines sont déclarées ici, d'autres plus haut, mais toutes indiquées pour mémoire
# CCM_FILE = os.path.normpath(os.path.join(DATA_FOLDER_ABSPATH, 'CrueConfigMetier.xml')) #: Chemin vers le fichier CCM
CCM = CrueConfigMetier()                                                                 #: Classe statique CCM
CCM.load(CCM_FILE)
