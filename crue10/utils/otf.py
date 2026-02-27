# coding: utf-8
# Imports généraux
import inspect
from typing import Any
import os.path
import numpy as np
import pprint

# Imports spécifiques
from crue10.utils.trace_back import trace_except
from crue10.utils.crueconfigmetier import CCM_FILE, CrueConfigMetier
from crue10.utils.configuration import Configuration
from crue10.etude import Etude

"""
Package pour un diff fonctionnel sur les objets Crue10.
PBa@CNR 2026-02 Création
"""

# Constante de module. Configuration par défaut pour utiliser CCM, complétée par Otf.json
CFG_OTF_DFT = {
    'dic_elt_sev': {            # Sévérité des différences, selon l'élément: 0 Anodine | 1 Mineure | 2 Majeure (défaut)
        'DIFF_TYPE': 2
    },
    'dic_elt_ccm': {            # Variables du CCM à utiliser pour la comparaison des valeurs, selon le type d'élément
    }
}

# Constante de module. Liste de méthodes intégrées à exclure de dir(obj)
LST_BUILTIN = [
    'append', 'clear', 'count', 'extend', 'index', 'insert', 'pop', 'remove', 'reverse', 'sort'
]


class OTF(object):
    """ Outil de Test Fonctionnel.
    Comparaison arborescente d'objets Crue10, en tenant compte du CrueConfigMetier.
    """

    @trace_except
    def __init__(self, ccm_path: str = CCM_FILE) -> None:
        """ Construire l'instance de classe.
        :param ccm_path: nom long du fichier de configuration CrueConfigMetier.xml
        """
        rep_src = os.path.dirname(__file__)     # Répertoire source d'OTF, pour localiser le fichier de configuration
        fic_cfg = os.path.join(rep_src, 'Otf.json')                 # Fichier de configuration, à côté de ce module
        self.cfg = Configuration(lst_cfg=[CFG_OTF_DFT, fic_cfg])    # Configuration pour utiliser CCM
        self._dic_desc = {}                     # Dictionnaire de description de la comparaison effectuée
        self._nbr_cmp = 0                       # Compteur des comparaisons effectuées
        self.ccm = CrueConfigMetier()           # Instance de CCM
        self.ccm.load(ccm_path)

    @trace_except
    def diff_crue10(self, nom_etu_a: str, nom_sce_a: str = None, nom_smo_a: str = None,
        nom_etu_b: str = None, nom_sce_b: str = None, nom_smo_b: str = None) -> dict:
        """ Renvoyer un dictionnaire des différences (fonctionnelles: analysées selon CCM) entre deux objets Crue10.
        Le parcours est récursif pour explorer l'arborescence interne des objets.
        :param nom_etu_a: nom long de la première étude
        :param nom_sce_a: nom du scénario de la première étude, par défaut tous les scénarios
        :param nom_smo_a: nom du sous-modèle de la première étude, par défaut tous les sous-modèles
        :param nom_etu_b: nom long de la seconde étude, par défaut identique à la première
        :param nom_sce_b: nom du scénario de la seconde étude, par défaut identique au premier
        :param nom_smo_b: nom du sous-modèle de la seconde étude, par défaut identique au premier
        :return: dictionnaire des différences {str_niv: {'sev': sev, 'a': var_a, 'b': var_b}} où str_niv décrit les
        niveaux de l'arborescence, sev indique la sévérité, var_a/var_b sont les valeurs en écart (None si absence)
        """
        # Traiter les entrées
        if nom_etu_b is None:
            nom_etu_b = nom_etu_a
        if nom_sce_b is None:
            nom_sce_b = nom_sce_a
        if nom_smo_b is None:
            nom_smo_b = nom_smo_a

        # Instancier les objects Crue10
        etu_a = Etude(nom_etu_a)
        sce_a = etu_a.get_scenario(nom_sce_a) if nom_sce_a else None
        mod_a = sce_a.modele if sce_a else None
        smo_a = mod_a.get_sous_modele(nom_smo_a) if mod_a and nom_smo_a else None
        etu_b = Etude(nom_etu_b)
        sce_b = etu_b.get_scenario(nom_sce_b) if nom_sce_b else None
        mod_b = sce_b.modele if sce_b else None
        smo_b = mod_b.get_sous_modele(nom_smo_b) if mod_b and nom_smo_b else None

        # Lire les données des objets Crue10 demandés
        obj_a = smo_a if smo_a else (mod_a if mod_a else (sce_a if sce_a else etu_a))
        obj_b = smo_b if smo_b else (mod_b if mod_b else (sce_b if sce_b else etu_b))
        obj_a.read_all(ignore_shp=True)
        obj_b.read_all(ignore_shp=True)

        # Description de la diff demandée
        nom_a, nom_b, nom_c = '', '', ''
        if nom_etu_a == nom_etu_b:
            nom_c = nom_etu_a
        else:
            nom_a = nom_etu_a
            nom_b = nom_etu_b
        if nom_sce_a == nom_sce_b and nom_c != '':
            nom_c += ('>' + nom_sce_a) if nom_sce_a else ''
        else:
            nom_a += (('>' if nom_a != '' else '') + nom_sce_a) if nom_sce_a else ''
            nom_b += (('>' if nom_a != '' else '') + nom_sce_b) if nom_sce_b else ''
        if nom_smo_a == nom_smo_b and nom_c != '':
            nom_c += ('>' + nom_smo_a) if nom_smo_a else ''
        else:
            nom_a += (('>' if nom_a != '' else '') + nom_smo_a) if nom_smo_a else ''
            nom_b += (('>' if nom_a != '' else '') + nom_smo_b) if nom_smo_b else ''
        self._dic_desc = {'a': nom_a, 'b': nom_b, 'c': nom_c}

        # Comparer les objets demandés
        return self.diff(obj_a, obj_b)

    @trace_except
    def diff(self, obj_a: object, obj_b: object, lst_niv: list|None = None) -> dict:
        """ Renvoyer un dictionnaire des différences (fonctionnelles: analysées selon CCM) entre deux objets Crue10.
        Le parcours est récursif pour explorer l'arborescence interne des objets.
        :param obj_a: premier objet
        :param obj_b: second objet
        :param lst_niv: liste des niveaux de l'arborescence pour les objets à examiner; None à la racine (liste vide)
        :return: dictionnaire des différences {str_niv: {'sev': sev, 'a': var_a, 'b': var_b}} où str_niv décrit les
        niveaux de l'arborescence, sev indique la sévérité, var_a/var_b sont les valeurs en écart (None si absence)
        """
        # Initialiser
        if lst_niv is None:
            lst_niv = []
        dic_dif = {}
        dic_var_a = self._get_var(obj_a, lst_niv)
        dic_var_b = self._get_var(obj_b, lst_niv)

        # Comparer les variables des deux objets (si les clés sont des path, on en prend juste le basename)
        lst_elt = []                            # Liste à valeurs uniques des clés à comparer, en respectant l'ordre
        [lst_elt.append(k) for k in dic_var_a.keys() if k not in lst_elt]
        [lst_elt.append(k) for k in dic_var_b.keys() if k not in lst_elt]
        for elt in lst_elt:
            # Récupérer les variables de chaque objet, selon une clé commune
            var_a = dic_var_a.get(elt, None)
            var_b = dic_var_b.get(elt, None)
            lst_niv_new = lst_niv + [elt]       # Ajouter un nouveau niveau
            self._comparer(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_niv=lst_niv_new)

        # Renvoyer les différences
        return dic_dif

    @trace_except
    def _get_var(self, obj: object, lst_niv: list) -> dict:
        """ Récupérer les variables internes d'un objet complexe: membres de l'instance, éléments d'un dictionnaire,
        éléments d'une liste, éléments d'un ndarray, etc.
        :param obj: objet complexe à examiner
        :param lst_niv: liste des niveaux de l'arborescence jusqu'à l'objet à examiner
        :return: dictionnaire {elt: var} où elt est la str représentant l'élément, et var la variable associée (Any)
        """
        # Traiter un cas limite
        if obj is None:
            return {}

        # Traiter un dictionnaire
        if isinstance(obj, dict):
            dic_var = {self._fmt_var(k, lst_niv): v for k, v in obj.items()}
            return dic_var

        # Traiter un tableau numpy: se ramener au cas d'une liste, traité juste après
        if isinstance(obj, np.ndarray):
            obj = list(obj) # Préféré à obj.tolist() afin de conserver des sous-éléments de type ndarray
  
        # Traiter une liste
        if isinstance(obj, list):
            dic_var = {}
            for var in obj:
                # Formater la clé selon CCM
                key = self._fmt_var(var, lst_niv)

                # Conserver chaque élément d'une série d'éléments identiques (en le suffixant par son numéro d'ordre)
                key_unq, i = key, 1
                while key_unq in dic_var:
                    i += 1
                    key_unq = f"{key}{i}"
                dic_var[key_unq] = var
            return dic_var

        # Traiter une instance de classe classique (ayant un dictionnaire de données)
        if hasattr(obj, '__dict__'):
            dic_var = vars(obj).copy()          # Copier les variables membres pour ne pas interférer
            return dic_var

        # Traiter une instance de classe sans dictionnaire de données (cas de xml.stree.ElementTree.Element)
        if isinstance(obj, object):
            dic_var = {}
            for attr in dir(obj):
                attr_ = getattr(obj, attr)
                if not attr.startswith('__') and not inspect.isroutine(attr_) and attr not in LST_BUILTIN:
                    # Exclure les fonctions et méthodes pour ne conserver a priori que les variables membres
                    dic_var[self._fmt_var(attr, lst_niv)] = attr_
            return dic_var

        # On ne devrait pas arriver ici: il doit manquer un traitement sur un type de variable
        print(f"! OTF._get_var impossible de récupérer les variables dans '{obj}', {type(obj)}")
        return {}

    @trace_except
    def _comparer(self, dic_dif: dict, var_a: Any, var_b: Any, lst_niv: list) -> None:
        """ Comparer les variables de différentes sources et remonter les différences significatives (selon CCM).
        :param dic_dif: dictionnaire des différences, à compléter
        :param var_a: première variable
        :param var_b: seconde variable
        :param lst_niv: liste des niveaux de l'arborescence de la comparaison à mener
        """
        self._nbr_cmp += 1

        # Traiter les différences d'existence ou de type
        if (var_a is None) and (var_b is None):
            return
        if (var_a is None) or (var_b is None):
            self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_niv=lst_niv)
            return
        if (type(var_a) != type(var_b)) and (self._get_itm(self.cfg['dic_elt_ccm'], lst_niv, niv=-1) is None):
            # Traiter les différences de type, sauf si le CCM permet de traiter cela ci-dessous
            lst_niv_new = lst_niv + ['DIFF_TYPE']   # Ajouter un nouveau niveau
            self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_niv=lst_niv_new)
            return

        # Traiter les différences sur les types simples
        if isinstance(var_a, str):
            # Traiter le cas particulier des path
            val_a = self._fmt_var(var_a, lst_niv)
            val_b = self._fmt_var(var_b, lst_niv)
            if not val_a == val_b:
                self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_niv=lst_niv)
            return
        if isinstance(var_a, bool) or isinstance(var_a, int) or isinstance(var_a, float) \
            or isinstance(var_a, complex) or isinstance(var_a, bytes) or isinstance(var_a, bytearray):
            # Comparer les variables simples en fonction de CCM, si applicable
            if not self._is_egal_ccm(var_a, var_b, lst_niv):
                self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_niv=lst_niv)
            return

        # Vérifier les différences sur les types complexes: parcours récursif
        if isinstance(var_a, np.ndarray):       # Tableau numpy
            # Tableau numpy: cas d'un tableau déjà analysé via CCM
            if self._get_itm(self.cfg['dic_elt_ccm'], lst_niv, niv=-2) is not None:
                if (var_a is None) or (var_b is None) or (len(var_a) != len(var_b)):
                    self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_niv=lst_niv)
                return
            # Tableau numpy: cas d'un tableau non analysé au préalable
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_niv=lst_niv)
            dic_dif.update(dif_new)
            return
        if isinstance(var_a, dict):             # Dictionnaire
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_niv=lst_niv)
            dic_dif.update(dif_new)
            return
        if isinstance(var_a, list):             # Liste
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_niv=lst_niv)
            dic_dif.update(dif_new)
            return
        if hasattr(var_a, '__dict__'):          # Instance de classe classique
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_niv=lst_niv)
            dic_dif.update(dif_new)
            return
        if isinstance(var_a, object):           # Instance de classe sans dictionnaire de données (xml.stree.ElementTree.Element)
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_niv=lst_niv)
            dic_dif.update(dif_new)
            return

        # On ne devrait pas arriver ici: il doit manquer une vérification sur un type de variable
        print(f"! OTF._comparer comparaison manquante '{lst_niv}', '{var_a}', '{var_b}', {type(var_a)}, {type(var_b)}")

    @trace_except
    def _get_itm(self, dic: dict, lst_niv: list, niv: int = -1) -> list | None:
        """ Récupérer un élément s'il existe pour la clé visée (correspondant à un niveau de l'arborescence), dans un
        dictionnaire de configuration.
        :param dic: dictionnaire de configuration dans lequel rechercher, exemples: sévérité, liste des variables CCM
        :param lst_niv: liste des niveaux de l'arborescence
        :param niv: niveau à récupérer: -1 pour le dernier, -2 pour l'avant-dernier, etc.
        :return: liste des variables CCM pour ce niveau, si elle existe; None sinon
        """
        # Récupérer le lien avec CCM, en fonction du dernier élément de la liste des niveaux
        if len(lst_niv) < abs(niv):
            return None
        return dic.get(lst_niv[niv], None)

    @trace_except
    def _fmt_var(self, var: Any, lst_niv: list) -> str|None:
        """ Formater la variable, si possible: selon id, selon basename, selon le CCM.
        :param var: variable à formater, éventuellement complexe
        :param lst_niv: liste des niveaux de l'arborescence
        :return: chaîne formatée ou None si var est None
        """
        # Traiter un cas limite
        if var is None:
            return None

        # Formater selon id si la variable est une instance de classe avec un id
        if hasattr(var, 'id'):
            return var.id

        # Formater selon basename si la variable est une chaîne de caractères avec un path
        if isinstance(var, str):
            if ('/' in var) or ('\\' in var):
                return os.path.basename(var)

        # Formater selon CCM, si la variable est décrite par le dernier élément de la liste des niveaux
        lst_var_ccm = self._get_itm(self.cfg['dic_elt_ccm'], lst_niv, niv=-1)   # Liste des variables CCM associées
        if lst_var_ccm is not None:
            # Élément décrit par CCM: formater selon l'epsilon de comparaison des variables
            try:
                lst_str = []
                for idx, var_ccm in enumerate(lst_var_ccm):
                    val = var[idx] if hasattr(var, '__getitem__') else var  # Valeur de la variable simple ou complexe
                    if self.ccm.variable[var_ccm].is_egal(val, 0):          # Protection contre -0. != +0.
                        val = 0
                    str_val = self.ccm.variable[var_ccm].txt_eps(val)       # Valeur avec ses chiffres significatifs
                    lst_str.append(f"{var_ccm}={str_val}")
                return f"[{', '.join(lst_str)}]"
            except Exception as e:
                print(f"! OTF._fmt_var incompatibilité avec Otf.json/dic_elt_ccm {var=} {lst_niv=} {lst_var_ccm=}: {repr(e)}")

        # Sinon formater en chaîne de caractères
        return str(var)

    @trace_except
    def _is_egal_ccm(self, var_a: Any, var_b: Any, lst_niv: list) -> bool:
        """ Comparer deux variables simples, si possible selon le CCM.
        :param var_a: première variable
        :param var_b: seconde variable
        :param lst_niv: liste des niveaux de l'arborescence
        :return: chaîne formatée
        """
        try:
            # Cas simple d'égalité
            if var_a == var_b:
                return True

            # Comparer selon CCM, si la variable est décrite par le dernier élément de la liste des niveaux
            lst_var_ccm = self._get_itm(self.cfg['dic_elt_ccm'], lst_niv, niv=-1)   # Liste des variables CCM associées
            if lst_var_ccm is None:
                # Élément non décrit par CCM
                return False
            else:
                # Élément décrit par CCM: comparer selon l'epsilon de comparaison des variables
                is_egal = True
                for idx, var_ccm in enumerate(lst_var_ccm):
                    # Récupérer les valeurs, dans le cas de variables simples ou complexes
                    val_a = var_a[idx] if hasattr(var_a, '__getitem__') else var_a
                    val_b = var_b[idx] if hasattr(var_b, '__getitem__') else var_b
                    # Tester l'égalité à l'epsilon de comparaison près
                    is_egal &= self.ccm.variable[var_ccm].is_egal(val_a, val_b)
                return is_egal
        except Exception as e:
            print(f"! OTF._is_egal_ccm incompatibilité avec Otf.json/dic_elt_ccm {var_a=}, {var_b=}, {lst_niv=}: {repr(e)}")

        # Fallback de l'exception: comparaison de chaînes formatées selon CCM
        val_a = self._fmt_var(var_a, lst_niv)
        val_b = self._fmt_var(var_b, lst_niv)
        return val_a == val_b

    @trace_except
    def _add_dif(self, dic_dif: dict, var_a: Any, var_b: Any, lst_niv: list) -> None:
        """ Ajouter une ligne de différence, en déterminant la sévérité.
        :param dic_dif: dictionnaire des différences, à modifier
        :param var_a: première variable
        :param var_b: seconde variable
        :param lst_niv: liste des niveaux de l'arborescence
        """
        # Formater l'arborescence de comparaison
        lst_niv_fmt = [self._fmt_var(niv, []) for niv in lst_niv]           # Formater l'arborescence, sans utiliser CCM
        str_niv = '>'.join(lst_niv_fmt)

        # Déterminer la sévérité: majeure par défaut, ou récupérée dans l'avant-dernier ou le dernier niveau
        sev = self._get_itm(self.cfg['dic_elt_sev'], lst_niv, niv=-2)       # Sévérité selon avant-dernière clé
        if sev is None:
            sev = self._get_itm(self.cfg['dic_elt_sev'], lst_niv, niv=-1)   # Sévérité selon dernière clé
        if sev is None:
            sev = 2

        # Enregistrer la ligne dans le dictionnaire des différences
        val_a = self._fmt_var(var_a, lst_niv)   # alternative: val_a = str(var_a) if var_a is not None else None
        val_b = self._fmt_var(var_b, lst_niv)   # alternative: val_b = str(var_b) if var_b is not None else None
        dif_new = {str_niv: {'sev': sev, 'a': val_a, 'b': val_b}}
        dic_dif.update(dif_new)

    @staticmethod
    @trace_except
    def nbr_dif(dic_dif: dict) -> dict:
        """ Renvoyer le nombre de différences par sévérité.
        :param dic_dif: dictionnaire des différences
        :return: dictionnaire du nombre de différences par sévérité
        """
        # Compter le nombre de différences par sévérité
        dic_nbr_dif = {}
        for k, v in dic_dif.items():
            sev = v['sev']
            dic_nbr_dif[sev] = dic_nbr_dif[sev] + 1 if sev in dic_nbr_dif else 1

        # Ordonner le dict par sévérité croissante
        return {k: v for k, v in sorted(dic_nbr_dif.items(), key=lambda x: x[0])}   # sorted renvoie des tuples

    @staticmethod
    @trace_except
    def filtrer(dic_dif: dict, niv_flt: int = 2) -> dict:
        """ Filter un dictionnaire des différences, en supprimant les niveaux bas.
        :param dic_dif: dictionnaire des différences de départ
        :param niv_flt: niveau de filtrage inclus; les niveaux strictement inférieurs sont supprimés
        :return: dictionnaire des différences filtré
        """
        return {k: v for k, v in dic_dif.items() if v['sev'] >= niv_flt}

    @property
    def dic_desc(self) -> dict:
        """ Renvoyer le dictionnaire de description de la comparaison effectuée.
        :return: dictionnaire avec clés: 'a' pour le premier objet, 'b' pour le second, 'c' pour la partie commune
        """
        return self._dic_desc

    @property
    def description(self) -> str:
        """ Renvoyer la description de la comparaison effectuée.
        :return: description des objets comparés
        """
        commun = f"sur '{self._dic_desc['c']}', " if self._dic_desc['c'] != '' else ''
        return f"diff_crue10 {commun}entre '{self._dic_desc['a']}' et '{self._dic_desc['b']}'"

    @property
    def nbr_cmp(self) -> int:
        """ Renvoyer le compteur de comparaisons effectuées.
        :return: nombre de comparaisons
        """
        return self._nbr_cmp


if __name__ == '__main__':
    """ Si lancement en tant que script.
    """
    dic_campagne = {
        'Etu_AS_CS_CI.etu.xml': {
            'nom_etu_a': r"C:\PROJETS\Enchaineur\Ossature\Modele_CA_g1.3\Etu_AS_CS_CI.etu.xml",
            'nom_sce_a': r"Sc_DCNC_1500_08_c0_1",
            'nom_smo_a': r"Sm_DCNC_1500_08_c0_1",
            'nom_etu_b': r"C:\PROJETS\Enchaineur\Ossature\Modele_CA_g1.3\Etu_AS_CS_CI.etu.xml",
            'nom_sce_b': r"Sc_DCNC_1500_08_c0_2",
            'nom_smo_b': r"Sm_DCNC_1500_08_c0_2"
        },
        'Etu_BV2024_Conc.etu.xml': {
            'nom_etu_a': r"C:\DATA\GéoRelai\Etu_BV2024_Conc_ori\Etu_BV2024_Conc.etu.xml",
            'nom_sce_a': r"Sc_BV2024-CalP-VR_RET",
            'nom_smo_a': r"Sm_BV2024-CalP-VR_RET",
            'nom_etu_b': r"C:\DATA\GéoRelai\Etu_BV2024_Conc\Etu_BV2024_Conc.etu.xml",
            # 'nom_sce_b': r"Sc_BV2024-CalP-VR_RET",
            # 'nom_smo_b': r"Sm_BV2024-CalP-VR_RET"
        },
        'Etu_BY2018_Conc.etu.xml': {
            'nom_etu_a': r"C:\DATA\GéoRelai\Etu_BY2018_Conc_ori\Etu_BY2018_Conc.etu.xml",
            'nom_sce_a': r"Sc_BY20_Conc",
            'nom_smo_a': r"Sm_BY20_OBLI_1",
            'nom_etu_b': r"C:\DATA\GéoRelai\Etu_BY2018_Conc\Etu_BY2018_Conc.etu.xml",
            # 'nom_sce_b': r"Sc_BY20_Conc",
            # 'nom_smo_b': r"Sm_BY20_OBLI_1"
        },
        'Etu_CA-AV.etu.xml': {
            'nom_etu_a': r"C:\DATA\GéoRelai\Etu_CA-AV_EDD_ori\Etu_CA-AV.etu.xml",
            'nom_sce_a': r"Sc_CA-AV_EDD_6",
            'nom_smo_a': r"Sm_CA-AV_EDD_601",
            'nom_etu_b': r"C:\DATA\GéoRelai\Etu_CA-AV_EDD\Etu_CA-AV.etu.xml",
            # 'nom_sce_b': r"Sc_CA-AV_EDD_6",
            # 'nom_smo_b': r"Sm_CA-AV_EDD_601"
        },
        'Etu_from_scratch.etu.xml': {
            'nom_etu_a': r"C:\DATA\GéoRelai\Etu_from_scratch_v2_import-v0.11.0_ori\Etu_from_scratch.etu.xml",
            'nom_sce_a': r"Sc_mono_sm_avec_bgefileau",
            'nom_smo_a': r"Sm_mono_sm_avec_bgefileau",
            'nom_etu_b': r"C:\DATA\GéoRelai\Etu_from_scratch_v2_import-v0.11.0\Etu_from_scratch.etu.xml",
            # 'nom_sce_b': r"Sc_mono_sm_avec_bgefileau",
            # 'nom_smo_b': r"Sm_mono_sm_avec_bgefileau"
        },
        'Etu_SV2019_Conc.etu.xml': {
            'nom_etu_a': r"C:\DATA\GéoRelai\Etu_SV2019_Conc_Br15\Etu_SV2019_Conc.etu.xml",
            'nom_sce_a': r"Sc_SV2019_Conc_EtatRef",
            'nom_smo_a': r"Sm_SV2019_Conc_EtatRef",
            'nom_etu_b': r"C:\DATA\GéoRelai\Etu_SV2019_Conc_Br15\Etu_SV2019_Conc.etu.xml",
            # 'nom_sce_b': r"Sc_SV2019_Conc_EtatRef",
            # 'nom_smo_b': r"Sm_SV2019_Conc_EtatRef"
        },
        'Etu_VS2021.etu.xml': {
            'nom_etu_a': r"C:\DATA\GéoRelai\Etu_VS2021_MEC_ori\Etu_VS2021.etu.xml",
            'nom_sce_a': r"Sc_VS_Mec_g0p0",
            'nom_smo_a': r"Sm_VS_Mec",
            'nom_etu_b': r"C:\DATA\GéoRelai\Etu_VS2021_MEC\Etu_VS2021.etu.xml",
            # 'nom_sce_b': r"Sc_VS_Mec_g0p0",
            # 'nom_smo_b': r"Sm_VS_Mec"
        },
    }

    for cas, dic_cas in dic_campagne.items():
        print(f"\n\n=== {cas} ===")
        otf = OTF(r'C:\PROJETS\Crue10_tools\crue10\data\CrueConfigMetier.xml')
        dic_diff = otf.diff_crue10(**dic_cas)
        pprint.pp(otf.filtrer(dic_diff, 0), width=300)
        print(f"Différences entre '{otf.dic_desc['a']}' et '{otf.dic_desc['b']}'")
        print(f"{len(dic_diff)} différences trouvées (sévérités: {otf.nbr_dif(dic_diff)}) sur {otf.nbr_cmp:_d} comparaisons")
