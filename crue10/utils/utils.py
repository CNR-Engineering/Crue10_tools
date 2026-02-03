# coding: utf-8

# Imports généraux WinPython
from typing import Any, Callable
import os
from pathlib import Path
import inspect
import shutil
import glob
import copy
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Imports spécifiques
from crue10.utils.trace_back import trace_except, cur_func
from crue10.utils.timer import time_it

"""
Utilitaires généraux:
- gestion des logs
- gestion des fichiers
- gestion des lst, dict, conversions
PBa@CNR 2023, 2024, 2025
"""


#: Gestion des logs
FIC_LOG = 'log.txt'                             # Nom par défaut du fichier de log

@trace_except
def log(msg: str = None, ecraser: bool = False, init: bool = False, fic_log: str = None) -> None:
    """ Écrire une ligne de compte-rendu dans un fichier de log; utile s'il n'y a qu'un seul fichier de log.
    :param msg: texte du message à écrire
    :param ecraser: option pour écrire à la suite de la ligne précédente (False) ou à sa place (True)
    :param init: option pour l'initialisation (efface les logs préexistants)
    :param fic_log: nom long éventuellement relatif du fichier de log
    """
    # Définir un fichier de log
    if not hasattr(log, 'fic_log'):             # S'assurer que la variable existe
        log.fic_log = FIC_LOG                   # Ainsi préfixée, sa valeur est retenue entre deux appels
    if fic_log is not None:
        log.fic_log = fic_log                   # Ainsi préfixé par le nom de la fonction, cette variable est retenue

    with open(log.fic_log, mode='a+t') as f:    # Fichier ouvert en écriture, curseur en fin de fichier
        # Effacer les logs préexistants
        if init:
            f.seek(0)                           # Se placer au début du fichier
            f.truncate()                        # Supprimer ce qui suit

        # Écraser la dernière ligne
        if ecraser:
            pos = f.tell() - len(os.linesep) - 1
            f.seek(pos)                         # Aller en fin de fichier sur un caractère non fin de ligne
            while pos > 0 and f.read(1) not in os.linesep:
                pos -= 1
                f.seek(pos)                     # Remonter jusqu'à trouver un caractère de fin de ligne
            if pos > 0 and f.read(1) in os.linesep:
                pos -= 1
                f.seek(pos)                     # Cas de Windows où le caractère de fin de ligne est double
            if pos > 0:
                f.seek(pos + 1)                 # Se placer sur le caractère suivant la fin de ligne trouvée
                f.truncate()                    # Supprimer ce qui suit

        # Écrire dans le fichier de log
        if msg is not None:
            # while msg[-1] in os.linesep:        # Supprimer les lignes inutiles en fin de msg
            #     msg = msg[:-1]
            f.write(msg + '\n')                 # Le '\n' ajouté est transformé en fonction du système


class Log(object):
    """ Classe de log vers un fichier, qui permet de gérer différents fichiers de logs.
    """

    @trace_except
    def __init__(self, fic_log: str = FIC_LOG, init: bool = True) -> None:
        """ Construire l'instance de classe.
        :param fic_log: nom long éventuellement relatif du fichier de log
        :param init: option pour l'initialisation (efface les logs préexistants)
        """
        self.fic_log = fic_log                  # Fichier de log, avec valeur par défaut
        fic = Path(self.fic_log)
        fic.parent.mkdir(parents=True, exist_ok=True)   # Créer le répertoire si inexistant
        if init:
            Log.__call__(self, init=init)

    def __call__(self, msg: str = None, ecraser: bool = False, init: bool = False,
        niv: str|None = 'INFO', dat: datetime = None, dur: timedelta = None) -> None:
        """ Écrire une ligne de compte-rendu; à appeler comme une fonction sur l'instance de classe.
        :param msg: texte du message à écrire
        :param ecraser: option pour écrire à la suite de la ligne précédente (False) ou à sa place (True)
        :param init: option pour l'initialisation (efface les logs préexistants)
        :param niv: niveau de sévérité du message (INFO | WARN | ERRNBLK | ERRBLK | FATAL)
        :param dat: date associée au mesage
        :param dur: durée associée au message
        """
        try:
            with open(self.fic_log, mode='a+t') as f:   # Fichier ouvert en écriture, curseur en fin de fichier
                # Effacer les logs préexistants
                if init:
                    f.seek(0)                   # Se placer au début du fichier
                    f.truncate()                # Supprimer ce qui suit

                # Écraser la dernière ligne
                if ecraser:
                    pos = max(0, f.tell() - len(os.linesep) - 1)    # Éviter une position négative
                    f.seek(pos)                 # Aller en fin de fichier sur un caractère non fin de ligne
                    while pos > 0 and f.read(1) not in os.linesep:
                        pos -= 1
                        f.seek(pos)             # Remonter jusqu'à trouver un caractère de fin de ligne
                    if pos > 0 and f.read(1) in os.linesep:
                        pos -= 1
                        f.seek(pos)             # Cas de Windows où le caractère de fin de ligne est double
                    if pos > 0:
                        f.seek(pos + 1)         # Se placer sur le caractère suivant la fin de ligne trouvée
                        f.truncate()            # Supprimer ce qui suit
                    if pos == 0:                # Cas du début de fichier
                        f.seek(0)               # Se placer au début du fichier
                        f.truncate()            # Supprimer ce qui suit

                # Écrire dans le fichier de log
                if msg is not None:
                    txt = ''
                    if niv is not None:
                        txt += f"{niv}\t"
                    if dat is not None:
                        txt += f"{dat:%Y/%m/%d %H:%M:%S}\t"
                    if dur is not None:
                        h, r = divmod(dur.total_seconds(), 3600)
                        m, r = divmod(r, 60)
                        s, r = divmod(r, 1)
                        txt += f"{int(h)}:{int(m):02d}:{int(s):02d}.{int(1000000*r):06d}\t"
                    txt += msg + '\n'           # Le '\n' ajouté est transformé en fonction du système
                    f.write(txt)
        except Exception as e:
            print(f"! Log exception {e}")
            pass                                # On ne veut pas qu'un dysfonctionnement de Log plante l'appli


def auto_adapt_call(decorator:Callable):
    """ Décorateur pour s'adapter à un appel de classmethod (avec self) ou de function/staticmethod (sans self).
    Il masque l'argument 'self' du décorateur.
    D'après https://stackoverflow.com/questions/1288498/using-the-same-decorator-with-arguments-with-functions-and-methods
    de Ants Aasma, Licence CC BY-SA 2.5
    """

    class _FuncDecoratorAdaptor(object):
        """ Inner-class pour s'adapter à un appel de classmethod (avec self) ou de function/staticmethod (sans self).
        """
        def __init__(self, decorator:Callable, func:Callable):
            self.decorator = decorator
            self.func = func

        def __call__(self, *args, **kwargs):
            return self.decorator(self.func)(*args, **kwargs)

        def __get__(self, instance: object, owner: type):
            return self.decorator(self.func.__get__(instance, owner))

    def adapt(func:Callable):
        """ Fonction décorateur elle-même.
        """
        return _FuncDecoratorAdaptor(decorator, func)

    # Renvoyer la fonction décorateur
    return adapt


def trace_except_log_fic(simple_log:Callable=print, global_fic_log:str='FIC_LOG', to_raise:bool=True) -> Callable:
    """ Définir un décorateur pour tracer (print | self.log:Log) les exceptions et leur origine.
    :param simple_log: fonction de tracé simple, 'print' par défaut
    :param global_fic_log: nom global référençant le fichier de log à utiliser avec la classe Log; astuce de passer en
        global pour pouvoir décorer les function et staticmethod sans recours à self.fic_log:str ou self.log:Log
    :param to_raise: True pour remonter l'exception | False pour seulement la tracer et continuer
    :return: méthode ou fonction décorée, renvoyant son résultat normal ou une exception
    """
    #@auto_adapt_call                           # Finalement, pas utile dans ce contexte; conservé pour l'inspiration
    def wrapper(func:Callable) -> Callable:
        """ Définir un décorateur pour tracer les exceptions et leur origine.
        :param func: méthode ou fonction à décorer
        :return: méthode ou fonction décorée, renvoyant son résultat normal ou une exception
        """
        def inner_wrapper(*args, **kwargs) -> Any:
            """ Wrapper appelant la méthode et l'enveloppant pour en récupérer les erreurs.
            :return: résultat normal ou exception
            """
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if simple_log is not None:
                    # Trace de log via une fonction simple comme 'print'
                    simple_log(f"!\tException '{func.__qualname__}': {repr(e)}")
                if global_fic_log in globals():
                    # Trace de log vers un fichier via 'Log'; le nom du fichier vient d'une variable globale
                    fic_log = globals()[global_fic_log]
                    log = Log(fic_log=fic_log, init=False)
                    log(f"Exception '{func.__qualname__}': {repr(e)}", niv='ERRBLK', dur=time_it())
                if to_raise:
                    # Remonter l'exception, ce qui bloque le reste du traitement
                    raise
        return inner_wrapper
    return wrapper


#: Gestion des fichiers
PATH = 'PATH'                                   #: Fonction abs_path, option pour récupérer le path complet
REP = 'REP'                                     #: Fonction abs_path, option pour récupérer le répertoire seul
FIC = 'FIC'                                     #: Fonction abs_path, option pour récupérer le fichier avec extension
NOM = 'NOM'                                     #: Fonction abs_path, option pour récupérer le fichier sans extension
EXT = 'EXT'                                     #: Fonction abs_path, option pour récupérer l'extension seule


@trace_except
def abs_path(*args, ret: str = PATH) -> str:
    """ Fonction utilitaire pour récupérer le path absolu d'un fichier.
    :param args: éléments à concaténer du path absolu ou relatif (par rapport au script d'appel) d'un fichier
    :param ret: 'PATH' pour le path complet / 'REP' pour le répertoire seul / 'FIC' pour le fichier avec extension /
                'NOM' pour le fichier sans extension / 'EXT' pour l'extension seule
    :return: path asbolu normalisé du fichier
    """
    # Assembler les éléments de path
    path = os.path.join(*args)

    # Transformer en path absolu
    if not os.path.isabs(path):
        fic_appel = inspect.stack()[2].filename     # Script d'appel: remonter pour échapper abs_path et trace_except
        rep_appel = os.path.dirname(fic_appel)      # Répertoire du script d'appel
        path = os.path.join(str(rep_appel), str(path))
    path = os.path.normpath(path)

    # Renvoyer l'élément demandé
    if ret == REP:
        # Renvoyer le répertoire
        return os.path.dirname(path)
    elif ret == FIC:
        # Renvoyer le fichier avec extension
        return os.path.basename(path)
    elif ret == NOM:
        # Renvoyer le fichier sans extension
        fic_ext = os.path.basename(path)
        lst = fic_ext.split('.')
        return '.'.join(lst[:-1]) if len(lst) > 1 else lst[0]
    elif ret == EXT:
        # Renvoyer l'extension seule
        fic_ext = os.path.basename(path)
        lst = fic_ext.split('.')
        return lst[-1]
    else:  # Cas ret == PATH:
        # Renvoyer le nom long du fichier
        return path


@trace_except
def copy_file(fic_src: str, rep_cib: str) -> int:
    """ Copier des fichiers vers un répertoire.
    :param fic_src: nom long du fichier source, éventuellement avec wildcard (exemple: *.txt)
    :param rep_cib: répertoire cible
    :return: nombre de fichiers copiés
    """
    if isinstance(fic_src, Path):
        fic_src = str(fic_src)
    if isinstance(rep_cib, Path):
        fic_src = str(rep_cib)
    nbr_copied = 0
    for fic in glob.glob(fic_src):
        shutil.copy(fic, rep_cib)
        nbr_copied += 1
    return nbr_copied


@trace_except
def is_file(fic: str) -> bool:
    """ Tester si (au moins) un fichier existe à cet emplacement.
    :param fic: nom long du fichier, éventuellement avec wildcard (exemple: *.txt)
    :return: True si existe; False sinon
    """
    return len(glob.glob(fic)) > 0


def json_load(*args, default=None) -> 'dict | list':
    """ Fonction utilitaire pour lire un fichier json.
    :param args: éléments à concaténer du path absolu ou relatif (par rapport au script d'appel) du fichier json à lire
    :param default: valeur par défaut à renvoyer si erreur dans la présence ou le contenu du fichier; exception sinon
    :return: contenu du fichier json monté sous forme de dictionnaire / liste
    """
    try:
        fic = abs_path(*args, ret='PATH')
        with open(fic, 'r', encoding='utf-8') as fi:
            return json.loads(fi.read())
    except (FileNotFoundError, json.JSONDecodeError) as e:
        if default is not None:
            return default
        print(f"! Exception {cur_func()}: {e}")
        raise
    except Exception as e:
        print(f"! Exception {cur_func()}: {e}")
        raise


def json_save(*args, dic: dict = None) -> None:
    """ Fonction utilitaire pour sauvegarder un dict vers un fichier json.
    :param args: éléments à concaténer du path absolu ou relatif (par rapport au script d'appel) du fichier json à lire
    :param dic: données à écrire
    """
    try:
        if dic is None:
            dic = {}
        fic = abs_path(*args, ret='PATH')
        rep = abs_path(fic, ret='REP')
        os.makedirs(rep, exist_ok=True)  # Créer l'arborescence des répertoires si besoin
        with open(fic, 'w') as f:
            json.dump(dic, f, indent=4)
    except FileNotFoundError as e:
        print(f"! Exception {cur_func()} FileNotFound: {e}")
        raise
    except Exception as e:
        print(f"! Exception {cur_func()}: {e}")
        raise


#: Gestion des lst, dict, conversions
@trace_except
def get_lst(obj: object) -> 'list | object':
    """ Fonction utilitaire pour se protéger contre une liste à 1 seul élément,
    par exemple pour éviter le parcours d'une chaîne caractère par caractère.
    :param obj: liste à protéger
    :return: liste, éventuellement à 1 seul élément, mais sous forme de liste
    """
    if isinstance(obj, str):                    # Cas d'une chaine
        return [obj]
    elif isinstance(obj, (np.ndarray, np.generic)):     # Cas d'un tableau numpy
        return obj.tolist()
    elif isinstance(obj, pd.Series):            # Cas sélection de DataFrame, qui donne une Series et non une list
        return obj.tolist()
    elif not isinstance(obj, list):             # Cas d'un seul élément
        return [obj]
    else:                                       # Cas par défaut, tout va bien !
        return obj


@trace_except
def lst_unique(lst: list) -> list:
    """ Renvoyer une liste sans doublon.
    :param lst: liste d'origine
    :return: liste sans doublon
    """
    lst_unq = []
    [lst_unq.append(elt) for elt in lst if elt not in lst_unq]
    return lst_unq


@trace_except
def add_unique(lst: list, elt: Any, to_end: bool = True) -> list:
    """ Ajouter un élément de manière unique dans une liste.
    :param lst: liste d'origine
    :param elt: élément à ajouter si pas déjà présent
    :param to_end: True pour ajouter en fin, False pour ajouter en début de liste
    :return: liste sans doublon
    """
    if lst is None:
        lst = []                                # Initialisier, au cas où...
    if elt not in lst:
        if to_end:
            lst.append(elt)                     # Ajouter en fin de liste
        else:
            lst.insert(0, elt)                  # Ajouter en fin de liste
    return lst


@trace_except
def dic_remove(dic_in: dict, lst_rem: list = None) -> dict:
    """ Fonction utilitaire pour supprimer une liste de clés dans un dictionnaire,
    et renvoyer un nouveau dictionnaire mis à jour.
    :param dic_in: dictionnaire de départ
    :param lst_rem: liste des clés à supprimer
    :return: nouveau dictionnaire
    """
    lst_rem = get_lst(lst_rem)
    return {k: v for k, v in dic_in.items() if k not in lst_rem}


@trace_except
def dic_filter(dic_in: dict, lst_flt: list = None) -> dict:
    """ Fonction utilitaire pour filtrer un dictionnaire en n'y laissant que certaines clés,
    et renvoyer un nouveau dictionnaire mis à jour.
    :param dic_in: dictionnaire de départ
    :param lst_flt: liste des clés à conserver; [] renvoit un dict vide; None renvoit une copie du dict original
    :return: nouveau dictionnaire
    """
    if lst_flt is None:
        return dic_in.copy()
    lst_flt = get_lst(lst_flt)
    return {k: v for k, v in dic_in.items() if k in lst_flt}


@trace_except
def dic_deep_update(dic_dft: dict, dic_dom: dict) -> dict:
    """ Fonction utilitaire pour compléter récursivement un dictionnaire,
    et renvoyer un nouveau dictionnaire mis à jour.
    :param dic_dft: dictionnaire à compléter (ses valeurs en doublon sont écrasées)
    :param dic_dom: dictionnaire complémentaire (ses valeurs en doublon sont dominantes)
    :return: nouveau dictionnaire, fusion des deux
    """
    # Vérifier les prérequis, ce qui fait une condition de sortie de la récursion
    if not isinstance(dic_dom, dict):
        return dic_dft
    if not isinstance(dic_dft, dict):
        return dic_dom

    # Créer un nouveau dictionnaire de manière récursive
    d = copy.copy(dic_dft)  # Shallow copy pour ne pas modifier l'original
    for k, v in dic_dom.items():
        if isinstance(v, dict):
            d[k] = dic_deep_update(d.get(k, {}),
                                   v)  # d.get(k, {}) renvoie la valeur par défaut (dict vide) si k absente
        else:
            d[k] = v
    return d


@trace_except
def interpol_dic(dat_cur: float, dat_deb: float, dat_fin: float, dic_val_deb: dict, dic_val_fin: dict) -> dict:
    """ Fonction utilitaire: interpoler linéairement entre deux dictionnaires {nom: val},
    et compléter les clés non communes par leur valeur présente dans un seul des deux dictionnaires.
    :param dat_cur: date courante, pour laquelle on veut récupérer le dictionnaire interpolé
    :param dat_deb: date de début de la période
    :param dat_fin: date de fin de la période
    :param dic_val_deb: dictionnaire pour le début de la période {nom: val}
    :param dic_val_fin: dictionnaire pour la fin de la période {nom: val}
    :return: dictionnaire dont les valeurs associées aux clés ont été interpolées
    """
    dic_val = {k: v for k, v in dic_val_deb.items() if v is not None}  # Par défaut, dic_val_deb si non-None
    for nom, val_fin in dic_val_fin.items():
        if val_fin is None:
            continue                            # Sauter à l'itération suivante si None
        if nom in dic_val_deb:                  # Interpoler sur les clés communes
            val_deb = dic_val_deb.get(nom)
            if dat_fin != dat_deb:
                val_cur = val_deb + (dat_cur - dat_deb) * (val_fin - val_deb) / (dat_fin - dat_deb)
            else:
                val_cur = val_fin
            dic_val[nom] = val_cur
        else:
            dic_val[nom] = val_fin              # Ajouter par défaut les clés de dic_val_fin
    return dic_val


def to_numeric(val: Any) -> Any:
    """ Convertir vers un type numérique si possible, renvoyer l'original sinon.
    :param val: valeur à convertir
    :return: valeur convertie
    """
    try:
        if val is None:
            return None
        val_float = float(val)
        val_int = int(val_float)
        if val_int - val_float == 0:
            return val_int
        else:
            return val_float
    except ValueError:
        return val
