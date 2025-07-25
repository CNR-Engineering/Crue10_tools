# coding: utf-8

# Imports généraux WinPython
import os
import inspect
from datetime import datetime, timedelta

"""
Utilitaires généraux pour les traces d'exécution et les exceptions.
PBa 2025
"""


#: Gestion des exceptions et traces
def trace_except(func: callable) -> any:
    """ Définir un décorateur pour tracer les exceptions et leur origine. Adapté aux méthodes ou aux fonctions.
    :param func: fonction ou méthode à décorer
    :return: retour normal ou remontée de l'exception
    """

    def wrapper(*args, **kwargs) -> any:
        """ Wrapper appelant la méthode ou la fonction et l'enveloppant pour en récupérer les erreurs.
        :param args: arguments simples (dont self pour une méthode)
        :param kwargs: arguments nommés
        :return: résultat normal ou exception
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Exception '{func.__qualname__}' ({os.path.basename(inspect.getfile(func))}): {repr(e)}")
            raise  # Remonter l'exception après l'avoir tracée

    return wrapper


def cur_file() -> str:
    """ Renvoyer le nom du fichier de l'appelant (utile pour des messages et logs).
    :return: nom long du fichier
    """
    return f"{inspect.stack()[1].filename}"


def cur_func() -> str:
    """ Renvoyer le nom de la fonction appelante (utile pour des messages et logs).
    :return: nom court du fichier et nom de la fonction
    """
    return f"{os.path.basename(inspect.stack()[1].filename)}\\{inspect.stack()[1].function}"


def cur_class() -> str:
    """ Renvoyer le nom de la classe appelante (utile pour des messages et logs).
    :return: nom de la classe
    """
    return f"{inspect.stack()[1][0].f_locals['self'].__class__.__name__}"


def cur_meth() -> str:
    """ Renvoyer le nom de la méthode appelante (utile pour des messages et logs).
    :return: nom de la classe et nom de la méthode
    """
    return f"{inspect.stack()[1][0].f_locals['self'].__class__.__name__}.{inspect.stack()[1].function}"


@trace_except
def time_it(reinit: bool = False) -> timedelta:
    """ Renvoyer le temps d'exécution depuis la dernière réinitialisation.
    :param reinit: True pour réinitialiser
    :return: durée depuis la dernière réinitialisation
    """
    if (not hasattr(time_it, 'dat_deb')) or reinit:     # Initialiser la variable si elle n'existe pas déjà;
        time_it.dat_deb = datetime.now()        # Date réinit; ainsi préfixée, la variable garde sa valeur entre appels
    return datetime.now() - time_it.dat_deb


@trace_except
def activ_period(period: int = 1, reinit: bool = False) -> bool:
    """ Renvoyer un booléen True périodiquement, False sinon.
    :param reinit: True pour réinitialiser
    :return: durée depuis la dernière réinitialisation
    """
    if (not hasattr(activ_period, 'compteur')) or reinit:   # Initialiser un compteur
        activ_period.compteur = -1              # Ainsi préfixée, la variable garde sa valeur entre les appels
    activ_period.compteur += 1                  # Incrémenter le compteur à chaque appel
    # True ssi le reste de la division entière nul, i.e. le compteur est un multiple de period
    return True if (activ_period.compteur % period) == 0 else False
