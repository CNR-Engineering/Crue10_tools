import numpy as np
from shapely.geometry import Point, LineString, LinearRing
import unittest

from crue10.emh.section import LoiFrottement, SectionProfil, SectionIdem, SectionInterpolee, SectionSansGeometrie
from crue10.utils import ExceptionCrue10


class SectionTestCase(unittest.TestCase):

    def setUp(self):
        self.section = SectionProfil('St_1')
        self.section.set_xz(np.array([(0.0, 1.0), (10.0, 0.0), (40.0, 0.0), (50.0, 1.0)]))
        self.section.set_lits_numerotes([0.0, 10.0, 20.0, 30.0, 40.0, 50.0])
        self.point = Point(0, 0)
        self.linestring = LineString([(0, 0), (1, 1)])
        self.linearring = LinearRing([(0, 0), (1, 1), (1, 0)])

    def test_summary(self):
        self.assertEqual(self.section.summary(), "SectionProfil #St_1: 4 points")

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

    def test_get_xt_merged_consecutive_lits_numerotes(self):
        desired = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0]
        actual = self.section.get_xt_merged_consecutive_lits_numerotes()
        self.assertEqual(actual, desired)

    def test_get_fond_moyen(self):
        desired = 0.2
        actual = self.section.get_fond_moyen('RD', 'RG')
        self.assertEqual(actual, desired)

    def test_get_fond_moyen_lit_actif(self):
        desired = 0.0
        actual = self.section.get_fond_moyen_lit_actif()
        self.assertEqual(actual, desired)
