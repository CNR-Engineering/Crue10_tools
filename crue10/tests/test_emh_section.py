# coding: utf-8
import numpy as np
from shapely.geometry import Point, LineString, LinearRing
import unittest

from crue10.emh.casier import Casier, ProfilCasier
from crue10.emh.noeud import Noeud
from crue10.emh.section import LoiFrottement, SectionProfil, SectionIdem, SectionInterpolee, SectionSansGeometrie
from crue10.utils import ExceptionCrue10


class SectionTestCase(unittest.TestCase):

    def setUp(self):
        self.section = SectionProfil('St_1')
        self.point = Point(0, 0)
        self.linestring = LineString([(0, 0), (1, 1)])
        self.linearring = LinearRing([(0, 0), (1, 1), (1, 0)])

    def test_loi_frottement(self):
        loi_frottement = LoiFrottement('Fk_1', 'Fk')
        loi_frottement.set_loi_Fk_values(np.array([(-15.0, 20.0)]))

        loi_frottement.set_loi_constant_value(30.0)
        self.assertEqual(loi_frottement.get_loi_Fk_value(), 30.0)

        loi_frottement.shift_loi_Fk_values(10.0)
        self.assertEqual(loi_frottement.get_loi_Fk_value(), 40.0)

        loi_frottement.set_loi_Fk_values(np.array([(200.0, 20.0), (230.0, 30.0)]))
        with self.assertRaises(ExceptionCrue10):
            loi_frottement.get_loi_Fk_value()

    def test_nom_section(self):
        pass
