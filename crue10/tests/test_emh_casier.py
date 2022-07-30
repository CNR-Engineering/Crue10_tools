import numpy as np
from shapely.geometry import Point, LineString, LinearRing
import unittest

from crue10.emh.casier import Casier, ProfilCasier
from crue10.emh.noeud import Noeud
from crue10.utils import ExceptionCrue10


class CasierTestCase(unittest.TestCase):

    def setUp(self):
        self.noeud = Noeud('Nd_1')
        self.point = Point(0, 0)
        self.linestring = LineString([(0, 0), (1, 1)])
        self.linearring = LinearRing([(0, 0), (1, 1), (1, 0)])

        self.profil_casier = ProfilCasier('Pc_1')
        self.profil_casier.longueur = 100.0
        self.profil_casier.set_xz(np.array([(0, 0), (10, 1), (20, -0.6)]))
        self.profil_casier.xt_min = 10

    def test_nom_profil_casier(self):
        with self.assertRaises(ExceptionCrue10):
            ProfilCasier('A')
        self.assertEqual(len(ProfilCasier('Pc_' + 'A').validate()), 1)
        self.assertEqual(len(ProfilCasier('Pc_' + 'A' * 30).validate()), 2)

    def test_profil_casier(self):
        self.assertEqual(len(self.profil_casier.validate()), 0)

    def test_profil_casier_compute_surface(self):
        self.assertEqual(self.profil_casier.compute_surface(-1.0), 0.0)
        self.assertEqual(self.profil_casier.compute_surface(0.0), 1.125)
        self.assertEqual(self.profil_casier.compute_surface(1.0), 13.0)
        self.assertEqual(self.profil_casier.compute_surface(2.0), 33.0)

    def test_profil_casier_compute_volume(self):
        self.assertEqual(self.profil_casier.compute_volume(2.0), 3300.0)

    def test_nom_casier(self):
        with self.assertRaises(ExceptionCrue10):
            Casier('A', self.noeud)
        self.assertEqual(len(Casier('Ca_' + 'A', self.noeud).validate()), 1)
        self.assertEqual(len(Casier('Ca_' + 'A' * 30, self.noeud).validate()), 2)

    def test_casier(self):
        Casier('Ca_1', self.noeud)
        with self.assertRaises(ExceptionCrue10):
            Casier('Ca_1', self.noeud.id)

    def test_casier_set_geom(self):
        casier = Casier('Ca_1', self.noeud)
        casier.set_geom(self.linearring)
        with self.assertRaises(ExceptionCrue10):
            casier.set_geom(self.point)
        with self.assertRaises(ExceptionCrue10):
            casier.set_geom(self.linestring)
