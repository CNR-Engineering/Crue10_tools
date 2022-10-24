import numpy as np
from numpy.testing import assert_array_almost_equal
from shapely.geometry import Point, LineString, LinearRing
import unittest

from crue10.emh.branche import BrancheSaintVenant, BrancheSeuilLateral
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
        branche = BrancheSeuilLateral('Br_seuil', self.noeud_amont, self.noeud_aval)
        branche.set_liste_elements_seuil_avec_coef_par_defaut(np.array([
            (85.86, 168.3),
            (104.98, 168.6),
            (270, 168.9),
            (29.86, 169.2),
            (13.95, 169.5),
            (8.55, 169.8),
        ]))

        branche.decouper_seuil_elem(100.0, 0.3)

        assert_array_almost_equal(branche.liste_elements_seuil[:, :2], np.array([
            (85.86, 168.3),
            (52.49, 168.55),
            (52.49, 168.65),
            (90, 168.825),
            (90, 168.9),
            (90, 168.975),
            (29.86, 169.2),
            (13.95, 169.5),
            (8.55, 169.8),
        ]))

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
