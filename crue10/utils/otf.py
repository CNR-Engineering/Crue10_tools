# coding: utf-8

# Imports généraux
from typing import Any
import numpy as np
import pprint

# Imports spécifiques
from crue10.utils.trace_back import trace_except
from crue10.utils.utils import lst_unique
from crue10.utils.crueconfigmetier import CCM_FILE, CrueConfigMetier
from crue10.etude import Etude

"""
Package pour un diff fonctionnel sur les objets Crue10.
PBa@CNR 2026-02 Création
"""

# Constante de module. Sévérité des différences, selon l'élément: 0 Anodine | 1 Mineure | 2 Majeure
DIC_ELT_SEV = {
    'files': 0,
    'id': 1,
    'Commentaire': 1,
    'comment': 1,
    'comment_profilsection': 1,
    'comment_loi': 1,
    'AuteurCreation': 1,
    'DateCreation': 1,
    'AuteurDerniereModif': 1,
    'DateDerniereModif': 1,
    'xz': 2,
    'xp': 2,
    'dz_section_reference': 2,
    'longueur': 2,
    'xt_min': 2,
    'liste_elements_seuil': 2,
    'liste_elements_barrage': 2,
    'DIFF_TYPE': 2,
}

# Constante de module. Variables du CCM à utiliser pour la comparaison des valeurs, selon le type d'élément.
DIC_ELT_CCM = {
    'xp': ['Xp'],
    'xz': ['Xt', 'Z'],
    'dz_section_reference': ['DzSectionIdem'],
    'longueur': ['Longueur'],
    'xt_min': ['Xt'],
    'xt_max': ['Xt'],
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

    @trace_except
    def __init__(self, ccm_path: str = CCM_FILE) -> None:
        """ Construire l'instance de classe.
        :param ccm_path: nom long du fichier de configuration CrueConfigMetier.xml
        """
        self.nbr_cmp = 0                        # Compteur des comparaisons effectuées
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
        etu_a = Etude(nom_etu_a)
        sce_a = etu_a.get_scenario(nom_sce_a) if nom_sce_a else None
        mod_a = sce_a.modele if sce_a else None
        smo_a = mod_a.get_sous_modele(nom_smo_a) if nom_smo_a else None
        etu_b = Etude(nom_etu_b) if nom_etu_b else etu_a
        sce_b = etu_b.get_scenario(nom_sce_b) if nom_sce_b else (etu_b.get_scenario(nom_sce_a) if nom_sce_a else None)
        mod_b = sce_b.modele if sce_b else None
        smo_b = mod_b.get_sous_modele(nom_smo_b) if nom_smo_b else mod_b.get_sous_modele(nom_smo_a) if nom_smo_a else None

        # Lire les objets Crue10 demandés
        obj_a = smo_a if smo_a else (mod_a if mod_a else (sce_a if sce_a else etu_a))
        obj_b = smo_b if smo_b else (mod_b if mod_b else (sce_b if sce_b else etu_b))
        obj_a.read_all(ignore_shp=True)
        obj_b.read_all(ignore_shp=True)

        # Comparer les objets demandés
        return self.diff(obj_a, obj_b)

    @trace_except
    def diff(self, obj_a: object, obj_b: object, lst_niv: list = None) -> dict:
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

        # Comparer les variables des deux objets
        lst_elt = lst_unique(list(dic_var_a.keys()) + list(dic_var_b.keys()))   # Liste à valeurs uniques des clés des
        for elt in lst_elt:                                                     # dict, en respectant l'ordre
            var_a = dic_var_a.get(elt, None)
            var_b = dic_var_b.get(elt, None)
            self._comparer(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_niv=lst_niv+[str(elt)])

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
            dic_var = {str(k): v for k, v in obj.items()}
            return dic_var

        # Traiter une liste
        if isinstance(obj, list):
            dic_var = {}
            for var in obj:
                # Formater la clé selon CCM
                key = self._fmt_ccm(var, lst_niv)

                # Conserver chaque élément d'une série d'éléments identiques (en le suffixant par son numéro d'ordre)
                key_unq, i = key, 1
                while key_unq in dic_var:
                    i += 1
                    key_unq = f"{key}{i}"
                dic_var[key_unq] = var
            return dic_var

        # Traiter un tableau numpy
        if isinstance(obj, np.ndarray):
            lst = list(obj) # Préféré à obj.tolist() afin de conserver des sous-éléments de type ndarray
            dic_var = {}
            for var in lst:
                # Formater la clé selon CCM
                key = self._fmt_ccm(var, lst_niv)

                # Conserver chaque élément d'une série d'éléments identiques (en le suffixant par son numéro d'ordre)
                key_unq, i = key, 1
                while key_unq in dic_var:
                    i += 1
                    key_unq = f"{key}{i}"
                dic_var[key_unq] = var
            return dic_var

        # Traiter une instance de classe
        if hasattr(obj, '__dict__'):
            return vars(obj).copy()             # Copier les variables membres pour ne pas interférer

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
        self.nbr_cmp += 1

        # Traiter les différences d'existence ou de type
        if (var_a is None) and (var_b is None):
            return
        if (var_a is None) or (var_b is None):
            self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_niv=lst_niv)
            return
        if type(var_a) != type(var_b):
            self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_niv=lst_niv+['DIFF_TYPE'])
            return

        # Traiter les différences sur les types simples
        if isinstance(var_a, bool) or isinstance(var_a, str) or isinstance(var_a, int) or isinstance(var_a, complex) \
            or isinstance(var_a, bytes) or isinstance(var_a, bytearray) or isinstance(var_a, float):
            # Comparer les variables simples en fonction de CCM, si applicable
            if not self._is_egal_ccm(var_a, var_b, lst_niv):
                self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_niv=lst_niv)
            return

        # Vérifier les différences sur les types complexes: parcours récursif
        if isinstance(var_a, dict):             # Dictionnaire
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_niv=lst_niv)
            dic_dif.update(dif_new)
            return
        if isinstance(var_a, list):             # Liste
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_niv=lst_niv)
            dic_dif.update(dif_new)
            return
        if isinstance(var_a, np.ndarray):       # Tableau numpy
            # Cas d'un tableau déjà analysé via CCM
            if len(lst_niv) > 1 and lst_niv[-2] in DIC_ELT_CCM:
                if (var_a is None) or (var_b is None) or (len(var_a) != len(var_b)):
                    self._add_dif(dic_dif=dic_dif, var_a=var_a, var_b=var_b, lst_niv=lst_niv)
                return

            # Cas d'un tableau non analysé au préalable
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_niv=lst_niv)
            dic_dif.update(dif_new)
            return
        if hasattr(var_a, '__dict__'):          # Instance de classe
            dif_new = self.diff(obj_a=var_a, obj_b=var_b, lst_niv=lst_niv)
            dic_dif.update(dif_new)
            return

        # On ne devrait pas arriver ici: il doit manquer une vérification sur un type de variable
        print(f"! OTF._comparer comparaison manquante '{lst_niv}', '{var_a}', '{var_b}', {type(var_a)}, {type(var_b)}")

    @trace_except
    def _is_egal_ccm(self, var_a: Any, var_b: Any, lst_niv: list) -> bool:
        """ Comparer deux variable simples, si possible selon le CCM.
        :param var: première variable
        :param var: seconde variable
        :param lst_niv: liste des niveaux de l'arborescence
        :return: chaîne formatée
        """
        try:
            # Cas simple d'égalité
            if var_a == var_b:
                return True

            # Récupérer le lien avec CCM, en fonction du dernier élément de la liste des niveaux
            lst_var_ccm = DIC_ELT_CCM.get(lst_niv[-1], None) if len(lst_niv) > 0 else None

            if lst_var_ccm is None:
                # Élément non présent dans DIC_ELT_CCM, et différent
                return False
            else:
                # Élément présent dans DIC_ELT_CCM: comparer selon l'epsilon de comparaison des variables
                is_egal = True
                for idx, var_ccm in enumerate(lst_var_ccm):
                    # Récupérer les valeurs, dans le cas de variables simples ou complexes
                    val_a = var_a[idx] if hasattr(var_a, '__getitem__') else var_a
                    val_b = var_b[idx] if hasattr(var_b, '__getitem__') else var_b
                    # Tester l'égalité à l'epsilon de comparaison près
                    is_egal &= self.ccm.variable[var_ccm].is_egal(val_a, val_b)
                return is_egal
        except Exception as e:
            print(f"! OTF._is_egal_ccm incompatibilité avec DIC_ELT_CCM {var_a=}, {var_b=}, {lst_var_ccm=}, {lst_niv=}: {repr(e)}")
            # Tenter un fallback: comparaison de chaînes formatées selon CCM
            return self._fmt_ccm(var_a, lst_niv) == self._fmt_ccm(var_b, lst_niv)

    @trace_except
    def _fmt_ccm(self, var: Any, lst_niv: list) -> str:
        """ Formater la variable, si possible selon le CCM.
        :param var: variable à formater, éventuellement complexe
        :param lst_niv: liste des niveaux de l'arborescence
        :return: chaîne formatée
        """
        # Récupérer le lien avec CCM, en fonction du dernier élément de la liste des niveaux
        lst_var_ccm = DIC_ELT_CCM.get(lst_niv[-1], None) if len(lst_niv) > 0 else None

        if lst_var_ccm is None:
            # Élément non présent dans DIC_ELT_CCM
            return f"{var}"
        else:
            # Élément présent dans DIC_ELT_CCM: formater selon l'epsilon de comparaison des variables
            try:
                str_key = '['
                for idx, var_ccm in enumerate(lst_var_ccm):
                    val = var[idx] if hasattr(var, '__getitem__') else var  # Valeur de la variable simple ou complexe
                    str_val = self.ccm.variable[var_ccm].txt_eps(val)       # Valeur avec ses chiffres significatifs
                    str_key += f"{var_ccm}={str_val}, "
                return str_key[0:-2] + ']'
            except Exception as e:
                print(f"! OTF._fmt_ccm incompatibilité avec DIC_ELT_CCM {var=} {lst_var_ccm=} {lst_niv=}: {repr(e)}")
                return f"{var}"

    @staticmethod
    @trace_except
    def _add_dif(dic_dif: dict, var_a: Any, var_b: Any, lst_niv: list) -> None:
        """ Ajouter une ligne de différence, en déterminant la sévérité.
        :param dic_dif: dictionnaire des différences, à modifier
        :param var_a: première variable
        :param var_b: seconde variable
        :param lst_niv: liste des niveaux de l'arborescence
        """
        # Formater l'arborescence de comparaison
        str_niv = '>'.join(lst_niv)

        # Déterminer la sévérité: majeure par défaut, ou récupérée dans l'avant-dernier ou le dernier niveau
        sev = DIC_ELT_SEV.get(lst_niv[-2]) if len(lst_niv) > 1 else None        # Sévérité selon avant-dernière clé
        if sev is None:
            sev = DIC_ELT_SEV.get(lst_niv[-1]) if len(lst_niv) > 0 else None    # Sévérité selon dernière clé
        if sev is None:
            sev = 2

        # Enregistrer la ligne dans le dictionnaire des différences
        val_a = str(var_a) if var_a is not None else None
        val_b = str(var_b) if var_b is not None else None
        dif_new = {str_niv: {'sev': sev, 'a': val_a, 'b': val_b}}
        dic_dif.update(dif_new)

    # @property
    # def nbr_cmp(self) -> int:
    #     """ Renvoyer le compteur de comparaisons effectuées.
    #     :return: nombre de comparaisons
    #     """
    #     return self.nbr_cmp


if __name__ == '__main__':
    """ Si lancement en tant que script.
    """
    # from crue10.utils.crueconfigmetier import CCM
    #
    # def explorer_ccm(typ: str, val: Any) -> str:
    #     str_val = CCM.variable[typ].txt(val, add_unt=True)
    #     nat = CCM.variable[typ].nat.nom
    #     dft = CCM.variable[typ].dft
    #     unt = CCM.variable[typ].nat.unt
    #     nrm_min = CCM.variable[typ].nrm_min
    #     nrm_max = CCM.variable[typ].nrm_max
    #     vld_min = CCM.variable[typ].vld_min
    #     vld_max = CCM.variable[typ].vld_max
    #     vld, msg = CCM.variable[typ].valider(val)
    #     return f"{typ=}, {nat=}, {str_val=}, {dft=}, {unt=}, {nrm_min=}, {nrm_max=}, {vld_min=}, {vld_max=}, {vld=}, {msg=}"
    #
    # print(explorer_ccm(typ='CoefD', val=0.9))   # Exemple d'une valeur valide
    # print(explorer_ccm(typ='CrMaxFlu', val=2))  # Exemple d'une valeur valide
    # print(explorer_ccm(typ='CoefD', val=1.1))   # Exemple d'une valeur anormale
    # print(explorer_ccm(typ='CoefD', val=-0.1))  # Exemple d'une valeur invalide
    # #print(explorer_ccm(typ='Inexistante', val=0.0))
    # print(explorer_ccm(typ='FormulePdc', val='BORDA'))
    # #vld, msg = CCM.enum['Inexistante'].valider('XXX')

    # nom_etu_a = r"C:\PROJETS\Enchaineur\Ossature\Modele_CA_g1.3\Etu_AS_CS_CI.etu.xml"
    # nom_sce_a = r"Sc_DCNC_1500_08_c0_1"
    # nom_smo_a = r"Sm_DCNC_1500_08_c0_1"
    # nom_etu_b = r"C:\PROJETS\Enchaineur\Ossature\Modele_CA_g1.3\Etu_AS_CS_CI.etu.xml"
    # nom_sce_b = r"Sc_DCNC_1500_08_c0_2"
    # nom_smo_b = r"Sm_DCNC_1500_08_c0_2"
    nom_etu_a = r"C:\DATA\GéoRelai\Etu_BV2024_Conc_ori\Etu_BV2024_Conc.etu.xml"
    nom_sce_a = r"Sc_BV2024-CalP-VR_RET"
    nom_smo_a = r"Sm_BV2024-CalP-VR_RET"
    nom_etu_b = r"C:\DATA\GéoRelai\Etu_BV2024_Conc\Etu_BV2024_Conc.etu.xml"
    nom_sce_b = r"Sc_BV2024-CalP-VR_RET"
    nom_smo_b = r"Sm_BV2024-CalP-VR_RET"

    otf = OTF(r'C:\PROJETS\Crue10_tools\crue10\data\CrueConfigMetier.xml')
    dic_diff = otf.diff_crue10(nom_etu_a=nom_etu_a, nom_sce_a=nom_sce_a, nom_smo_a=nom_smo_a,
        nom_etu_b=nom_etu_b, nom_sce_b=nom_sce_b, nom_smo_b=nom_smo_b)
    pprint.pp(dic_diff, width=300)
    print(f"{len(dic_diff)} différences trouvées sur {otf.nbr_cmp} comparaisons effectuées")
