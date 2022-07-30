import numpy as np
from shapely.geometry import Point, LineString, LinearRing
import unittest

from crue10.emh.branche import BrancheSaintVenant
from crue10.emh.noeud import Noeud
from crue10.utils import ExceptionCrue10


class BrancheTestCase(unittest.TestCase):

    def setUp(self):
        self.noeud_amont = Noeud('Nd_1')
        self.noeud_aval = Noeud('Nd_2')

    def test_nom_branche(self):
        with self.assertRaises(ExceptionCrue10):
            BrancheSaintVenant('A', self.noeud_amont, self.noeud_aval)
        self.assertEqual(len(BrancheSaintVenant('Br_' + 'A', self.noeud_amont, self.noeud_aval).validate()), 1)
        self.assertEqual(len(BrancheSaintVenant('Br_' + 'A' * 30, self.noeud_amont, self.noeud_aval).validate()), 2)

    def test_branche(self):
        with self.assertRaises(ExceptionCrue10):
            BrancheSaintVenant('Br_1', self.noeud_amont, self.noeud_amont)

    # Branche
    def test_ajouter_section_dans_branche(self):
        pass

    def test_set_geom(self):
        pass

    def test_normalize_sections_xp(self):
        pass

    # BrancheAvecElementsSeuil
    def test_branche_avec_elements_seuil_decouper_seuil_elem(self):
        pass

    def test_branche_avec_elements_seuil_get_min_z(self):
        pass

    # BrancheOrifice
    def test_branche_orifice_get_min_z(self):
        pass

    # BrancheBarrageFilEau
    def test_branche_barrage_fil_eau_loi_QpilZam(self):
        pass

    # BrancheSaintVenant
    def test_branche_saint_venant_valide(self):
        pass
