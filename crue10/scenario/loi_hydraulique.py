# coding: utf-8
import numpy as np

from crue10.utils import check_isinstance, check_preffix, ExceptionCrue10


class LoiHydraulique:
    """
    Loi hydraulique = tableau de valeurs de dimension 2 (temporels ou non)

    Loi DF: loi avec temps horodaté
    Loi FF: loi sans temps horodaté

    :ivar id: nom de la loi hydraulique
    :vartype id: str
    :ivar type: type de la loi hydraulique
    :vartype type: str
    :ivar date_zero: date zéro
    :vartype date_zero: str
    :ivar values: tableau de valeurs, shape=(nb_values, 2)
    :vartype values: np.ndarray
    """

    TYPES = ['LoiTQapp', 'LoiTZimp', 'LoiQZimp', 'LoiTOuv', 'LoiTQruis', 'LoiQQ', 'LoiQOuv', 'LoiZZimp']

    def __init__(self, nom_loi, type, comment=''):
        """
        :param nom_loi: nom de la loi hydraulique
        :type nom_loi: str
        :param type: type de loi (parmi `TYPES`)
        :type type: str
        :param comment: commentaire optionnel
        :type comment: str
        """
        check_preffix(nom_loi, 'Loi')
        self.id = nom_loi
        if type not in LoiHydraulique.TYPES:
            raise ExceptionCrue10("Le type de loi `%s` n'est pas supporté" % type)
        self.type = type
        self.date_zero = None
        self.comment = comment
        self.values = None

    def est_temporel(self):
        """
        Est une chronique temporelle (ie. l'abscisse correspond au temps)
        """
        return self.type.startswith('LoiT')

    def set_date_zero(self, date_zero):
        """
        Définir la date zéro

        :param date_zero: date zéro
        :type date_zero: str
        """
        # TODO use a datetime instead of a string
        check_isinstance(date_zero, str)
        self.date_zero = date_zero

    def set_values(self, values):
        """
        Définir le tableau de valeurs

        :param values: tableau de valeurs, shape=(nb_values, 2)
        :type values: np.ndarray
        """
        check_isinstance(values, np.ndarray)
        if values.shape[1] != 2:
            raise ExceptionCrue10("La loi hydraulique n'a pas 2 valeurs")
        self.values = values

    def __repr__(self):
        return "LoiHydraulique %s (%i lignes)" % (self.id, 0 if self.values is None else len(self.values))
