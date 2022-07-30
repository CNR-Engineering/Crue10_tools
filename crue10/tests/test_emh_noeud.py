from shapely.geometry import Point, LineString, LinearRing
import unittest

from crue10.emh.noeud import Noeud
from crue10.utils import ExceptionCrue10


class NoeudTestCase(unittest.TestCase):

    def setUp(self):
        self.noeud = Noeud('Nd_1')
        self.point = Point(0, 0)
        self.linestring = LineString([(0, 0), (1, 1)])
        self.linearring = LinearRing([(0, 0), (1, 1), (1, 0)])

    def test_nom_noeud(self):
        with self.assertRaises(ExceptionCrue10):
            Noeud('A')
        self.assertEqual(len(Noeud('Nd_' + 'A').validate()), 0)
        self.assertEqual(len(Noeud('Nd_' + 'A' * 30).validate()), 1)

    def test_noeud_set_geom(self):
        self.noeud.set_geom(self.point)
        with self.assertRaises(ExceptionCrue10):
            self.noeud.set_geom(self.linestring)
        with self.assertRaises(ExceptionCrue10):
            self.noeud.set_geom(self.linearring)
