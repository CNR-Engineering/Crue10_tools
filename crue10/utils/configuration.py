# coding: utf-8

# Imports généraux WinPython
import copy
from typing import Any
# from PyQt5.QtCore import QObject, pyqtSignal

# Imports spécifiques
from crue10.utils.trace_back import trace_except
from utils import abs_path, get_lst, json_load, json_save, dic_deep_update

"""
Classe de gestion de configurations.
- Permet de faire le lien entre fichiers de sauvegarde et un dictionnaire utilisable dans le code.
- Supporte des sources de configuration en cascade.
Idée:
- Envoie des signaux en cas de sauvegarde ou de modif de la config (afin de pouvoir gérer un indicateur de modif).
PBa@CNR 2024-09 Création
"""


class Configuration(object):    # Idée: hériter de QObject pour gérer les signaux
    """ Gestionnaire de configuration, sous la forme d'un dictionnaire.
    """
    # Variables de classe: signaux personnalisés
    # sgl_saved = pyqtSignal()                    # Signal configuration sauvegardée
    # sgl_unsaved = pyqtSignal()                  # Signal configuration modifiée non sauvegardée

    @trace_except
    def __init__(self, lst_cfg: list | str = None, fic_sav: str = 'user.json') -> None:
        """ Initialiser l'instance.
        :param lst_cfg: liste des sources de configuration, du moins spécifique au plus spécifique (dict ou json)
        :param fic_sav: fichier json pour sauvegarder la configuration utilisateur
        """
        # Construire la classe mère
        #super().__init__()                      # Classe mère QObject pour les signaux

        # Déclarer les variables membres de l'instance
        self.cfg = {}                           # Dictionnaire contenant la configuration
        self.cfg_statique = {}                  # Configuration hors celle correspondant au fichier de sauvegarde
        self.fic_sav = abs_path(fic_sav)        # Fichier json pour sauvegarder la configuration

        # Récupérer la configuration d'après les sources
        if lst_cfg is None:
            lst_cfg = [{}]                      # Configuration vide, par défaut
        for cfg in get_lst(lst_cfg):
            self._add_cfg(cfg)                  # Du moins spécifique au plus spécifique

    @trace_except
    def __setitem__(self, key: Any, value: Any) -> None:
        """ Ajouter ou modifier une valeur de configuration via l'opérateur []; émettre un signal unsaved (si modifiée).
        :param key: clé de configuration
        :param value: valeur de configuration
        """
        if self.__getitem__(key) != value:
            self.cfg[key] = value
            # self.sgl_unsaved.emit()             # Émettre le signal

    @trace_except
    def __getitem__(self, key: Any) -> Any:
        """ Renvoyer une valeur de configuration via l'opérateur [].
        :param key: clé de configuration
        :return: valeur correspondant à la clé, ou None
        """
        return self.cfg.get(key)                # None si pas de correspondance

    @trace_except
    def get(self, key: Any, dft_val=None) -> Any:
        """ Renvoyer une valeur de configuration via l'opérateur get.
        :param key: clé de configuration
        :param dft_val: valeur par défaut, si la clé n'existe pas
        :return: valeur correspondant à la clé, ou None
        """
        return self.cfg.get(key, dft_val)       # dft_val si pas de correspondance

    @trace_except
    def __contains__(self, key: Any) -> bool:
        """ Vérifier si une clé est contenue dans la configuration via l'opérateur in.
        :param key: clé de configuration
        :return: True si contenue, False sinon
        """
        return key in self.cfg

    @trace_except
    def _add_cfg(self, itm: str | dict, dominante: bool = True) -> None:
        """ Ajouter un élément dans la configuration.
        :param itm: fichier contenant un dictionnaire ou dictionnaire
        :param dominante: indique si la nouvelle configuration est prioritaire sur la préexistante
        :return: mise à jour de self.cfg
        """
        # Récupérer le nouvel élément de configuration
        cfg = None
        if itm is None:                         # Si itm n'est pas défini, alors on ne peut rien faire
            pass
        elif isinstance(itm, str):              # Cas d'une chaine: nom d'un fichier json contenant un dict de cfg
            itm = abs_path(itm)
            cfg = json_load(itm, default={})
        elif isinstance(itm, dict):             # Cas d'un dict de cfg
            cfg = itm

        # Supprimer les clés de valeur None
        if cfg is not None:
            cfg = {k: v for k, v in cfg.items() if v is not None}

        # Compléter la configuration connue avec ce nouvel élément
        if dominante:
            self.cfg = dic_deep_update(         # Compléter self.cfg avec nouvelle cfg dominante
                dic_dft=self.cfg, dic_dom=cfg)
        else:
            self.cfg = dic_deep_update(         # Compléter self.cfg avec nouvelle cfg complémentaire
                dic_dft=cfg, dic_dom=self.cfg)

        # Conserver une trace de la cfg statique, i.e. hors celle correspondant au fichier de sauvegarde
        # Note: cela n'est pertinent que si celle du fichier de sauvegarde est dominante, i.e. ajoutée en dernier
        if itm != self.fic_sav:
            self.cfg_statique = copy.deepcopy(self.cfg)

    @trace_except
    def save(self, diff: bool = True) -> None:
        """ Sauvegarder la configuration sous la forme d'un fichier; émettre un signal saved.
        :param diff: True pour ne sauvegarder que les différences par rapport à la cfg statique; False pour tout prendre
        """
        # Dictionnaire à sauvegarder
        if diff:
            # Extraire la cfg spécifique, i.e. hors celle statique
            cfg_sav = self._diff(self.cfg, self.cfg_statique)
        else:
            # Sauvegarder toute la cfg
            cfg_sav = self.cfg

        # Sauvegarder la configuration utilisateur et avertir
        json_save(self.fic_sav, dic=cfg_sav)
        # self.sgl_saved.emit()                   # Émettre le signal

    @trace_except
    def _diff(self, itm: object, itm_ref: object) -> object:
        """ Comparer résursivement des objets de type dict, list, variables simples et sortir leurs différences.
        :param itm: objet à analyser (sa config devrait être la plus complète)
        :param itm_ref: objet de référence (sa config devrait être moins étendue)
        :return: dictionnaire ou autre objet contenant les écarts constatés
        """
        if isinstance(itm, list) and isinstance(itm_ref, list):
            # Cas de listes
            return itm

        elif isinstance(itm, dict) and isinstance(itm_ref, dict):
            # Cas de dictionnaires
            diff = {}
            for k, v in itm.items():
                if k not in itm_ref:
                    diff[k] = v
                elif v != itm_ref[k]:
                    diff[k] = self._diff(v, itm_ref[k])
            return diff

        elif type(itm) is not type(itm_ref):
            # Cas d'objets de types différents portant le même nom
            return itm

        elif itm != itm_ref:
            # Cas d'objets différents portant le même nom
            return itm

        else:
            # On devrait être dans le cas d'objets de type simple identiques
            return None


if __name__ == '__main__':
    from datetime import timedelta
    CFG_DFT = {                                 # Exemple de cfg applicative par défaut
        'is_maximized': False,                  # Exemple bool
        'nbr_run': 0,                           # Exemple int
        'dur_sce': 3600.0,                      # Exemple float
        'pdt_ench': timedelta(seconds=300.),    # Exemple autre type, ici timedelta
        'rep_etu': None,                        # Exemple None
        'fic_etu': None,
        'nom_sce': None,
        'nom_run': "R0000-00-00-00h00m00s",     # Exemple str
        'lst_nom_courbe': []                    # Exemple list
    }

    # Exemple d'une configuration avec valeurs par défaut CFG_DFT et valeurs de l'utilisateur
    # Il peut y avoir plusieurs étages: CFG_DFT < 'cfg_appli.json' < 'user.json'
    cfg_ = Configuration([CFG_DFT, '../user.json'], fic_sav=r'../user.json')   # Configuration fusionnée
    dur_sce = cfg_['dur_sce']                   # Exemple de récupération depuis la cfg
    cfg_['nom_sce'] = 'Sc_BY'                   # Exemple de mémorisation dans la cfg
    cfg_.save()                                 # Sauvegarde de la config utilisateur (clés spécifiques uniquement)
