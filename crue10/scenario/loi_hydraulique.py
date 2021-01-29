# coding: utf-8
import numpy as np

from crue10.utils import check_isinstance, check_preffix, ExceptionCrue10


class LoiHydraulique:
    """Loi DF: loi avec temps horodaté"""

    TYPES = ['LoiTQapp', 'LoiTZimp', 'LoiQZimp', 'LoiTOuv', 'LoiTQruis', 'LoiQQ', 'LoiQOuv', 'LoiZZimp']

    def __init__(self, nom_loi, type, comment=''):
        check_preffix(nom_loi, 'Loi')
        self.id = nom_loi
        if type not in LoiHydraulique.TYPES:
            raise ExceptionCrue10("Le type de loi `%s` n'est pas supporté" % type)
        self.type = type
        self.date_zero = None
        self.comment = comment
        self.values = None

    def has_time(self):
        return self.type.startswith('LoiT')

    def set_date_zero(self, date_zero):
        # TODO use a datetime instead of a string
        check_isinstance(date_zero, str)
        self.date_zero = date_zero

    def set_values(self, values):
        check_isinstance(values, np.ndarray)
        if values.shape[1] != 2:
            raise ExceptionCrue10("La loi hydraulique n'a pas 2 valeurs")
        self.values = values

    def __repr__(self):
        return "LoiHydraulique %s (%i lignes)" % (self.id, 0 if self.values is None else len(self.values))
