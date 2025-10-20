"""
Utilitaires généraux pour l'inspection des fonctions et méthodes (utile pour les traces d'exécution et les exceptions).
PBa 2025
"""
import inspect
import os


#: Gestion des exceptions
def trace_except(func: callable) -> callable:
    """ Définir un décorateur pour tracer (print) les exceptions et leur origine. Adapté aux méthodes ou aux fonctions.
    :param func: fonction ou méthode à décorer
    :return: méthode ou fonction décorée, renvoyant son résultat normal ou une exception
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
            raise                               # Remonter l'exception après l'avoir tracée
    return wrapper


def trace_except_log(fn_log: callable = print) -> callable:
    """ Définir un décorateur pour tracer les exceptions et leur origine. Adapté aux méthodes ou aux fonctions.
    :param fn_log: fonction de tracé à utiliser, son prototype doit être log(txt: str) -> None
    :return: méthode ou fonction décorée, renvoyant son résultat normal ou une exception
    """
    def inner_trace_except(func: callable) -> callable:
        """ Définir un décorateur pour tracer les exceptions et leur origine. Adapté aux méthodes ou aux fonctions.
        :param func: fonction ou méthode à décorer
        :return: méthode ou fonction décorée
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
                fn_log(f"Exception '{func.__qualname__}' ({os.path.basename(inspect.getfile(func))}): {repr(e)}")
                raise                           # Remonter l'exception après l'avoir tracée
        return wrapper
    return inner_trace_except


#: Gestion du contexte courant: fichier source, fonction, classe et méthode
def cur_file(monter: int = 1) -> str:
    """ Renvoyer le nom du fichier de l'appelant (utile pour des messages et logs).
    :param monter: nombre de niveau à remonter pour accéder à l'appelant visé
    :return: nom long du fichier
    """
    return f"{inspect.stack()[monter].filename}"


def cur_func(monter: int = 1) -> str:
    """ Renvoyer le nom de la fonction appelante (utile pour des messages et logs).
    :param monter: nombre de niveau à remonter pour accéder à l'appelant visé
    :return: nom court du fichier et nom de la fonction
    """
    return f"{os.path.basename(inspect.stack()[monter].filename)}\\{inspect.stack()[monter].function}"


def cur_class(monter: int = 1) -> str:
    """ Renvoyer le nom de la classe appelante (utile pour des messages et logs).
    :param monter: nombre de niveau à remonter pour accéder à l'appelant visé
    :return: nom de la classe
    """
    return f"{inspect.stack()[monter][0].f_locals['self'].__class__.__name__}"


def cur_meth(monter: int = 1) -> str:
    """ Renvoyer le nom de la méthode appelante (utile pour des messages et logs).
    :param monter: nombre de niveau à remonter pour accéder à l'appelant visé
    :return: nom de la classe et nom de la méthode
    """
    return f"{inspect.stack()[monter][0].f_locals['self'].__class__.__name__}.{inspect.stack()[monter].function}"
