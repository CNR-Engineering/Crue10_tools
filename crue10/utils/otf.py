# coding: utf-8

# Imports généraux
from typing import Any
import math
import numpy as np
import pprint

# Imports spécifiques
from crue10.utils.crueconfigmetier import CCM_FILE, CrueConfigMetier
from crue10.etude import Etude

"""
Package pour un diff fonctionnel sur les objets Crue10.
PBa@CNR 2026-01 Création
"""

# Constantes de module
DIC_KEY_SEV = {                                 # Sévérité des diff.: 0 Anodine | 1 Mineure | 2 Majeure | 3 Anomalie
    'files': 0,
    'id': 1,
    'Commentaire': 1,
    'AuteurCreation': 1,
    'DateCreation': 1,
    'AuteurDerniereModif': 1,
    'DateDerniereModif': 1,
    'xz': 2,
    'liste_elements_seuil': 2,
    'liste_elements_barrage': 2,
    'DIFF_TYPE': 3,
}
DIC_KEY_CCM = {                                 # Variables du CCM à utiliser
    'xz': ['Xt', 'Z'],
    'liste_elements_seuil': ['Largeur', 'Zseuil', 'CoefD', 'CoefPdc'],
    'liste_elements_barrage': ['Largeur', 'Zseuil', 'CoefNoy', 'CoefDen'],
    'Largeur': ['Largeur'],
    'CoefBeta': ['CoefBeta'],
    '_loi_Fk': ['Z', 'K'],
    'loi_QPdc': ['Q', 'Pdc']
}


class OTF(object):
    """ Outil de Test Fonctionnel.
    Comparaison arborescente d'objets Crue10, en tenant compte du CrueConfigMetier.
    """

    def __init__(self, ccm_path: str = CCM_FILE):
        self.ccm = CrueConfigMetier()
        self.ccm.load(ccm_path)

    def diff(self, obj_a: object, obj_b: object, lst_key: list = None) -> dict:
        # Initialiser
        if lst_key is None:
            lst_key = []
        dic_dif = {}
        dic_var_a, dic_var_b = self._get_var(obj_a, lst_key), self._get_var(obj_b, lst_key)
        dic_var_b_restant = dic_var_b.copy()

        # Comparer les dictionnaires de variables des deux objets
        for key, val_a in dic_var_a.items():
            # Parcourir les éléments de dic_var_a et rechercher les correspondances dans dic_var_b
            val_b = dic_var_b.get(key, None)    # Renvoie None si pas de correspondance
            lst_key_new = lst_key + [str(key)]
            self._chk_dif(dic_dif=dic_dif, var_a=val_a, var_b=val_b, lst_key=lst_key_new)
            if val_b is not None:
                dic_var_b_restant.pop(key)      # Ne pas modifier dic_var_b

        for key, val_b in dic_var_b_restant.items():
            # Parcourir les éléments restants dans dic_var_b, n'ayant donc pas de correspondance dans dic_var_a
            lst_key_new = lst_key + [str(key)]
            self._chk_dif(dic_dif=dic_dif, var_a=None, var_b=val_b, lst_key=lst_key_new)

        return dic_dif

    def _get_var(self, obj: object, lst_key: list) -> dict:
        """ Récupérer un dictionnaire de variables de l'objet: membres de l'instance, éléments d'un dictionnaire,
        éléments d'une liste, éléments d'un ndarray, etc.
        :param obj: objet à examiner; instance de classe, dictionnaire, liste, etc.
        :param lst_key: liste des clés, correspondant aux niveaux de l'arbre parcouru
        :return: dictionnaire {variable: valeur}
        """
        # Traiter un cas limite
        if obj is None:
            return {}

        # Traiter les types complexes
        if isinstance(obj, dict):               # Dictionnaire
            return obj
        if isinstance(obj, list):               # Liste
            dic_var = {}
            for elt in obj:
                key = self._fmt_ccm(elt, lst_key)   # Formater la clé selon CCM
                key_unq, i = key, 1
                while key_unq in dic_var:
                    i += 1
                    key_unq = f"{key}{i}"
                dic_var[key_unq] = elt          # Conserver chaque élément d'une liste d'éléments identiques
            return dic_var
        if isinstance(obj, np.ndarray):         # Tableau numpy
            lst = list(obj) # Préféré à obj.tolist() afin de conserver des elt de type ndarray
            dic_var = {}
            for elt in lst:
                key = self._fmt_ccm(elt, lst_key)   # Formater la clé selon CCM
                key_unq, i = key, 1
                while key_unq in dic_var:
                    i += 1
                    key_unq = f"{key}{i}"
                dic_var[key_unq] = elt          # Conserver chaque élément d'une liste d'éléments identiques
            return dic_var
        if hasattr(obj, '__dict__'):            # Instance de classe
            return vars(obj).copy()             # Copie des variables membres pour ne pas interférer

        # On ne devrait pas se retrouver ici: il doit manquer une vérification sur un type de variable
        print(f"! ANOMALIE OTF._get_var '{obj}', {type(obj)}")

    def _chk_dif(self, dic_dif: dict, var_a: Any, var_b: Any, lst_key: list) -> None:
        # Vérifier les différences d'existence ou de type
        if (var_a is None) and (var_b is None):
            return
        if var_a is None:
            self._add_dif(dic_dif=dic_dif, var_a=None, var_b=var_b, lst_key=lst_key)
            return
        if var_b is None:
            self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=None, lst_key=lst_key)
            return
        if type(var_a) != type(var_b):
            self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_key=lst_key+['DIFF_TYPE'])
            return

        # Vérifier les différences sur les types simples
        if isinstance(var_a, bool) or isinstance(var_a, str) or isinstance(var_a, int) or isinstance(var_a, complex) \
            or isinstance(var_a, bytes) or isinstance(var_a, bytearray):
            if var_a != var_b:
                self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_key=lst_key)
            return
        if isinstance(var_a, float):
            if var_a != var_b:
                if self._fmt_ccm(var_a, lst_key) != self._fmt_ccm(var_b, lst_key):  # Vérifier plus finement avec CCM
                    self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_key=lst_key)
            return

        # Vérifier les différences sur les types complexes
        if isinstance(var_a, dict):             # Dictionnaire
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_key=lst_key)
            dic_dif.update(dif_new)
            return
        if isinstance(var_a, list):             # Liste
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_key=lst_key)
            dic_dif.update(dif_new)
            return
        if isinstance(var_a, np.ndarray):       # Tableau numpy
            # Cas d'un tableau déjà analysé via CCM
            if len(lst_key) > 1 and lst_key[-2] in DIC_KEY_CCM:
                if (var_a is None) or (var_b is None) or (len(var_a) != len(var_b)):
                    self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_key=lst_key)
                return
            # Cas d'un tableau non analysé au préalable
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_key=lst_key)
            dic_dif.update(dif_new)
            return
        if hasattr(var_a, '__dict__'):          # Instance de classe
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_key=lst_key)
            dic_dif.update(dif_new)
            return

        # On ne devrait pas se retrouver ici: il doit manquer une vérification sur un type de variable
        print(f"! ANOMALIE OTF._chk_dif '{lst_key}', '{var_a}', '{var_b}', {type(var_a)}, {type(var_b)}")

    def _fmt_ccm(self, elt: Any, lst_key: list) -> str:
        """ Formater la clé pour le dictionnaire des variables, si possible selon le CCM.
        :param elt: élément pour lequel on cherche une clé
        :param lst_key: niveaux de l'arborescence de comparaison
        :return: chaîne formatée
        """
        # Récupérer le lien avec le CCM, en fonction du dernier élément de lst_key
        lst_var_ccm = DIC_KEY_CCM.get(lst_key[-1], None) if len(lst_key) > 0 else None

        if lst_var_ccm is None:
            # Élément non présent dans DIC_KEY_CCM
            return f"{elt}"
        else:
            # Élément présent dans DIC_KEY_CCM: formater la clé selon l'epsilon de comparaison du type des variables
            try:
                str_key = '['
                for idx, var_ccm in enumerate(lst_var_ccm):
                    var = elt[idx] if hasattr(elt, '__getitem__') else elt
                    eps = self.ccm.variable[var_ccm].eps    # TODO récupérer directement CCM.variable[var_ccm].fmt_eps ou .txt_eps(elt[idx])
                    if isinstance(eps, float):
                        fmt = f".{abs(min(0,math.floor(math.log10(eps))))}f"
                        str_key += f"{var_ccm}={var:{fmt}}, "
                    else:
                        str_key += f"{var_ccm}={int(var):d}, "
                return str_key[0:-2] + ']'
            except Exception as e:  #TODO Exception si elt incompatible
                raise e

    def _add_dif(self, dic_dif: dict, var_a: Any, var_b: Any, lst_key: list) -> None:
        """ Ajouter une ligne de différence, en affectant la sévérité.
        :param dic_dif: dictionnaire des différences, à modifier
        :param var_a:
        :param var_b:
        :param lst_key:
        """
        str_key = '>'.join(lst_key)             # L'arborescence de comparaison est séparée par ce caractère
        sev = DIC_KEY_SEV.get(lst_key[-2]) if len(lst_key) > 1 else None        # Sévérité selon avant-dernière clé
        if sev is None:
            sev = DIC_KEY_SEV.get(lst_key[-1]) if len(lst_key) > 0 else None    # Sévérité selon dernière clé
        if sev is None:
            sev = 2                             # Sévérité majeure par défaut
        dif_new = {str_key: {'sev': sev, 'a': str(var_a), 'b': str(var_b)}}
        dic_dif.update(dif_new)

if __name__ == '__main__':
    """ Si lancement en tant que script.
    """
    nom_etu_a = r"C:\PROJETS\Enchaineur\Ossature\Modele_CA_g1.3\Etu_AS_CS_CI.etu.xml"
    nom_sce_a = r"Sc_DCNC_1500_08_c0_1"
    nom_smo_a = r"Sm_DCNC_1500_08_c0_1"
    nom_etu_b = r"C:\PROJETS\Enchaineur\Ossature\Modele_CA_g1.3\Etu_AS_CS_CI.etu.xml"
    nom_sce_b = r"Sc_DCNC_1500_08_c0_2"
    nom_smo_b = r"Sm_DCNC_1500_08_c0_2"

    etu_a = Etude(nom_etu_a)
    sce_a = etu_a.get_scenario(nom_sce_a)
    sce_a.read_all(ignore_shp=True)
    mod_a = sce_a.modele
    smo_a = mod_a.get_sous_modele(nom_smo_a)
    etu_b = Etude(nom_etu_b)
    sce_b = etu_b.get_scenario(nom_sce_b)
    sce_b.read_all(ignore_shp=True)
    mod_b = sce_b.modele
    smo_b = mod_b.get_sous_modele(nom_smo_b)

    otf = OTF()
    dic_dif = otf.diff(smo_a, smo_b)
    pprint.pp(dic_dif, width=300)
