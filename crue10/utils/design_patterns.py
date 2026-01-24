# coding: utf-8

# Imports généraux
from typing import Callable
from importlib import import_module

# Imports spécifiques
from crue10.utils import ExceptionCrue10

"""
Ensemble d'utilitaires mettant en œuvre divers design patterns.
- Singleton
- Factory
PBa 2025-06 Création
"""


class Singleton(type):
    """ Classe à utiliser comme une métaclasse pour mettre en œuvre le design pattern Singleton.
    Cela permet d'instancier une classe à divers endroits du code, en n'en ayant qu'une seule et unique instance.
    """
    # Variable de classe: dictionnaire des instances {}
    _dic_nom_obj = {}

    def __call__(cls, *args, **kwargs) -> any:
        """ Fournir une instance de la classe, en la créant seulement la première fois.
        """
        if cls not in cls._dic_nom_obj:
            cls._dic_nom_obj[cls] = super(Singleton, cls).__call__(*args, **kwargs)  # Appeler le constructeur, une fois
        return cls._dic_nom_obj[cls]            # Renvoyer une instance déjà créée


class FactoryClass(metaclass=Singleton):
    """ Classe utilitaire mettant en œuvre le design pattern Factory.
    Cela permet de définir une classe associée à un type, pour ensuite pouvoir l'instancier en late binding.

    Ensemble cohérent: 'FactoryClass', 'factory_define', 'factory_make' (les deux fonctions constituent l'interface).

    - Usage 1: spécialiser une classe de Crue10_tools dans un autre package, sans toucher à Crue10_tools:
      - définir une classe spécialisée pour un certain type: @factory_define('Etude') avant class EtudeSpec(Etude)
      - instancier la dernière déclaration trouvée: etu = factory_make('Etude')(etu_path='path/to/Etu_XX.etu.xml')

    - Usage 2: instancier une classe d'après son nom:
      - définir une classe pour un certain type: FactoryClass().define('ModEnch', nom_mod='Crue10e', nom_cls='Crue10e')
      - instancier cette classe: mod = factory_make('ModEnch', nom_cls='Crue10e')(mod_id='GE', mbr='00')
    """
    # Variable de classe: liste des dictionnaires de configuration connus [{
    #     'typ_cls': str,                       # Nom associé au type de classe générique
    #     'ord': int,                           # Ordre de définition des classes à instancier pour un type générique
    #     'cls': type,                          # Classe à instancier
    #     'nom_mod': str,                       # Nom du module de la classe à instancier
    #     'nom_cls': str,                       # Nom de la classe à instancier
    #     'cnd': str }]                         # Condition à évaluer pour choisir la classe à instancier
    _lst_cfg_cls = []

    def define(self, typ_cls: str, cls: type = None, nom_mod: str = None, nom_cls: str = None, cnd: str = None) -> None:
        """ Définir une association entre un nom et une classe.

        :param typ_cls: nom associé au type de classe (classe générique)
        :param cls: classe à utiliser (classe à instancier)
        :param nom_mod: nom du module de la classe (classe à instancier, alternative au passage de cls)
        :param nom_cls: nom de la classe (classe à instancier, alternative au passage de cls)
        :param cnd: condition à évaluer pour choisir une classe
        """
        ord = 0                                 # Ordre de définition de cls pour un typ_cls particulier
        for cfg_cls in self._lst_cfg_cls:
            if cfg_cls['typ_cls'] == typ_cls:
                ord = max(ord, cfg_cls['ord'])
        ord += 1
        self._lst_cfg_cls.append(
            {'typ_cls': typ_cls, 'ord': ord, 'cls': cls, 'nom_mod': nom_mod, 'nom_cls': nom_cls, 'cnd': cnd})

    def make(self, typ_cls: str, nom_cls: str = None) -> type:
        """ Fournir la classe à partir du nom qui lui est associé.

        :param typ_cls: nom associé au type de classe (classe générique)
        :param nom_cls: nom de la classe à instancier; par défaut la dernière définie pour typ_cls
        :return: classe à utiliser
        """
        # Créer la liste ordonnée des cfg pour typ_cls
        lst_cfg_cls = [cfg_cls for cfg_cls in self._lst_cfg_cls if (cfg_cls['typ_cls']==typ_cls)]
        lst_cfg_cls.sort(key=lambda x: x['ord'])

        # Renvoyer la classe à instancier si correspondance avec nom_cls
        if nom_cls is not None:
            for cfg_cls in lst_cfg_cls:
                if cfg_cls['nom_cls'] == nom_cls:
                    return self._get_cls(typ_cls, cfg_cls['cls'], cfg_cls['nom_mod'], nom_cls)

        # Sinon, renvoyer la classe à instancier pour la dernière déclaration de typ_cls
        cfg_cls = lst_cfg_cls[-1]
        return self._get_cls(typ_cls, cfg_cls['cls'], cfg_cls['nom_mod'], nom_cls)

    def make_cnd(self, typ_cls: str, **kwargs) -> type:
        """ Fournir la classe à partir du nom qui lui est associé et de la vérification d'une condition,
        évaluée dans l'ordre de définition des classes.

        :param typ_cls: nom associé au type de classe (classe générique)
        :param kwargs: arguments nommés pour l'évaluation de la condition de choix d'une classe particulière
        :return: classe à utiliser
        """
        # Trouver la classe
        cls, nom_mod, nom_cls = self.get_from_cnd(typ_cls, **kwargs)

        # Renvoyer la classe à instancier
        return self._get_cls(typ_cls, cls, nom_mod, nom_cls)

    def get_from_cnd(self, typ_cls: str, **kwargs) -> tuple[type, str, str]:
        """ Trouver la classe à partir du nom qui lui est associé et de la vérification d'une condition,
        évaluée dans l'ordre de définition des classes.

        :param typ_cls: nom associé au type de classe (classe générique)
        :param kwargs: arguments nommés pour l'évaluation de la condition de choix d'une classe particulière
        :return: (classe, nom du module, nom de la classe)
        """
        # Créer la liste ordonnée des cfg pour typ_cls
        lst_cfg_cls = [cfg_cls for cfg_cls in self._lst_cfg_cls \
            if ((cfg_cls['typ_cls']==typ_cls) and (cfg_cls['cnd'] is not None))]
        lst_cfg_cls.sort(key=lambda x: x['ord'])    #, reverse=True)

        # Évaluer la condition, dans l'ordre de définition des classes
        for cfg_cls in lst_cfg_cls:
            cnd = cfg_cls['cnd']
            if cnd is not None:
                try:
                    str_cnd = cnd.format(**kwargs)  # Compléter la condition avec les arguments
                    if eval(str_cnd):
                        return cfg_cls['cls'], cfg_cls['nom_mod'], cfg_cls['nom_cls']
                except:
                    pass                            # La condition n'a pas pu être évaluée
        raise ExceptionCrue10(f"FactoryClass ne trouve pas le type '{typ_cls}' pour les conditions: {kwargs}")

    def _get_cls(self, typ_cls: str, cls: type, nom_mod: str, nom_cls: str) -> type:
        """ Renvoyer la cls à instancier

        :param typ_cls: nom associé au type de classe (classe générique)
        :param cls: classe à instancier
        :param nom_mod: nom du module de la classe à instancier
        :param nom_cls: nom de la classe à instancier
        :return: classe à instancier
        """
        if cls is not None:
            return cls                                          # Renvoyer la classe demandée
        if (nom_mod is not None) and (nom_cls is not None):
            cls = getattr(import_module(nom_mod), nom_cls)      # Importer dynamiquement la classe (late binding)
            return cls                                          # Renvoyer la classe demandée
        if nom_cls is None:
            raise ExceptionCrue10(f"FactoryClass ne connait pas le type '{typ_cls}'")
        else:
            raise ExceptionCrue10(f"FactoryClass ne connait pas la classe '{nom_cls}' pour le type '{typ_cls}'")

def factory_define(typ_cls: str) -> Callable:
    """ Décorateur qui associe le nom du type passé en paramètre à la classe décorée; pour ensuite utiliser 'factory'.

    Ensemble cohérent: 'FactoryClass', 'factory_define', 'factory_make'.

    Usage: @factory_define('Etude') avant class EtudeSpec(Etude)

    :param typ_cls: nom associé au type de classe (classe générique)
    """
    def decorator(cls: type) -> type:
        """ Récupérer la classe décorée pour pouvoir l'utiliser via 'factory'.

        :param cls: classe décorée
        :return: classe définie
        """
        FactoryClass().define(typ_cls=typ_cls, cls=cls)     # Définir l'association entre typ_cls et cls
        return cls
    return decorator


def factory_make(typ_cls: str, nom_cls: str = None) -> type:
    """ Renvoyer la classe associée à un nom de type.

    Ensemble cohérent: 'FactoryClass', 'factory_define', 'factory_make'.

    Usage 1: etu = factory_make('Etude')(etu_path='path/to/Etu_XX.etu.xml')
    Usage 2: mod = factory_make('ModEnch', nom_cls='Crue10e')(mod_id='GE', mbr='00')

    :param typ_cls: nom associé au type de classe (classe générique)
    :param nom_cls: nom de la classe à instancier; par défaut la dernière définie pour typ_cls
    :return: classe associée
    """
    return FactoryClass().make(typ_cls=typ_cls, nom_cls=nom_cls)
