# coding: utf-8

"""
Ensemble d'utilitaires mettant en œuvre divers design patterns.
- Singleton
- Factory
© CNR
PBa 2025-06 Création
"""


class Singleton(type):
    """ Classe à utiliser comme une métaclasse pour mettre en œuvre le design pattern Singleton.
    Cela permet d'instancier une classe à divers endroits du code, en n'en ayant qu'une seule et unique instance.
    """
    # Variable de classe: dictionnaire des instances {}
    _dic_nom_obj = {}

    def __call__(cls, *args, **kwargs):
        """ Fournir une instance de la classe, en la créant seulement la première fois.
        """
        if cls not in cls._dic_nom_obj:
            cls._dic_nom_obj[cls] = super(Singleton, cls).__call__(*args, **kwargs)  # Appeler le constructeur, une fois
        return cls._dic_nom_obj[cls]            # Renvoyer une instance déjà créée


class FactoryClass(metaclass=Singleton):
    """ Classe utilitaire mettant en œuvre le design pattern Factory.
    Cela permet de récupérer une classe associée à un nom, pour ensuite l'instancier en late binding. On peut ainsi
    spécialiser une classe de Crue10_tools dans un autre package, sans toucher à Crue10_tools.
    Ensemble cohérent: 'FactoryClass', 'factory_define', 'factory_make' (les deux fonctions constituent l'interface).
    """
    # Variable de classe: dictionnaire d'association {nom_cls: cls}
    _dic_nom_cls = {}

    def define(self, nom_cls: str, cls: callable) -> None:
        """ Définir une association entre un nom et une classe.
        :param nom_cls: nom associé
        :param cls: classe à utiliser
        """
        # print(f"Définir '{nom_cls}' comme {cls}")
        self._dic_nom_cls[nom_cls] = cls

    def make(self, nom_cls: str) -> callable:
        """ Fournir la classe à partir du nom qui lui est associé.
        :param nom_cls: nom associé
        :return: classe à utiliser
        """
        # print(f"Utiliser '{nom_cls}' comme {self._dic_nom_cls.get(nom_cls)}")
        return self._dic_nom_cls.get(nom_cls)


def factory_define(nom_cls: str):
    """ Décorateur qui associe le nom passé en paramètre à la classe décorée; pour ensuite utiliser 'factory'.
    Ensemble cohérent: 'FactoryClass', 'factory_define', 'factory_make'.
    :param nom_cls: nom associé à la classe
    """
    def decorator(cls: callable):
        """ Récupérer la classe décorée pour pouvoir l'utiliser via 'factory'.
        :param cls: classe décorée
        :return: classe définie
        """
        FactoryClass().define(nom_cls, cls)     # Mémoriser l'association entre nom_cls et cls
        return cls
    return decorator


def factory_make(nom_cls: str) -> callable:
    """ Renvoyer la classe associée à un nom; utiliser le décorateur '@factory_define' sur la classe pour l'associer.
    Ensemble cohérent: 'FactoryClass', 'factory_define', 'factory_make'.
    Exemple d'utilisation: etu = factory_make('Etude')(etu_path=r"path/to/Etu_XX.etu.xml")
    :param nom_cls: nom associé à la classe à renvoyer
    :return: classe associée
    """
    return FactoryClass().make(nom_cls)
