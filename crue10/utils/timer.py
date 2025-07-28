# coding: utf-8

# Imports généraux WinPython
from datetime import datetime, timedelta

# Imports spécifiques
from crue10.utils.traceback import trace_except

"""
Utilitaires généraux pour les traces d'exécution et les exceptions.
PBa 2025
"""


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
    :param period: nombre d'appels depuis la réinitialisation avant d'avoir un True en retour
    :param reinit: True pour réinitialiser
    :return: True si on est sur un multiple de period; False sinon
    """
    if (not hasattr(activ_period, 'compteur')) or reinit:   # Initialiser un compteur
        activ_period.compteur = -1              # Ainsi préfixée, la variable garde sa valeur entre les appels
    activ_period.compteur += 1                  # Incrémenter le compteur à chaque appel
    # True ssi le reste de la division entière nul, i.e. le compteur est un multiple de period
    return True if (activ_period.compteur % period) == 0 else False
