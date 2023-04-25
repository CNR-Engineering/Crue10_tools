# coding: utf-8
from filecmp import cmp
import numpy as np
import os.path
import unittest

from crue10.etude import Etude
from crue10.tests import DATA_TESTS_FOLDER_ABSPATH, WRITE_REFERENCE_FILES
from crue10.utils import ExceptionCrue10
from crue10.utils.settings import CSV_DELIMITER, FMT_FLOAT_CSV, VERSION_GRAMMAIRE_COURANTE


FOLDER_IN = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_COURANTE)
FOLDER_OUT = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'out', VERSION_GRAMMAIRE_COURANTE)


class ModeleTestCase(unittest.TestCase):

    def setUp(self):
        etude = Etude(os.path.join('crue10', 'tests', 'data', 'in', '1.2', 'Etu3-6', 'Etu3-6.etu.xml'))
        self.modele = etude.get_modele('Mo_M3-6_c10')
        self.modele.read_all()
        self.branches = self.modele.get_liste_branches_entre_deux_noeuds('Nd_N1', 'Nd_N5')

    def test_get(self):
        # SousModele
        self.assertEqual(self.modele.get_sous_modele('Sm_M3-6_c10').id, 'Sm_M3-6_c10')

        # Noeud
        self.assertEqual(self.modele.get_noeud('Nd_N1').id, 'Nd_N1')

        # Casier
        casier = self.modele.get_casier('Ca_N7')
        self.assertEqual(casier.id, 'Ca_N7')

        # ProfilCasier
        profil_casier = casier.profils_casier[0]
        self.assertEqual(profil_casier.id, 'Pc_N7_001')
        self.assertEqual(profil_casier.longueur, 200.0)
        self.assertTrue((profil_casier.xz == np.array([(0, 0.2), (100, 0.2)])).all())

    def test_get_liste(self):
        self.assertEqual([noeud.id for noeud in self.modele.get_liste_noeuds()],
                         ['Nd_N1', 'Nd_N2', 'Nd_N6', 'Nd_N3', 'Nd_N4', 'Nd_N7', 'Nd_N5'])
        self.assertEqual([casier.id for casier in self.modele.get_liste_casiers()],
                         ['Ca_N7', 'Ca_N6'])
        self.assertEqual([section.id for section in self.modele.get_liste_sections()],
                         ['St_Prof11', 'St_B1_00050', 'St_PROF10', 'St_B1_00150', 'St_PROF9', 'St_B1_00250',
                          'St_PROF8', 'St_B1_00350', 'St_PROF7', 'St_B1_00450', 'St_PROF6A', 'St_PROF6B', 'St_PROF5',
                          'St_PROF4', 'St_PROF3A', 'St_PROF3AM', 'St_PROF3AV', 'St_PROF3B', 'St_PROF2', 'St_PROF1',
                          'St_PROFSTR1', 'St_PROFSTR2', 'St_B5_Am', 'St_B5_Av', 'St_B8_Am', 'St_B8_Av'])
        self.assertEqual([branche.id for branche in self.modele.get_liste_branches()],
                         ['Br_B1', 'Br_B2', 'Br_B3', 'Br_B4', 'Br_B6', 'Br_B5', 'Br_B8'])
        self.assertEqual([loi.id for loi in self.modele.get_liste_lois_frottement()],
                         ['FkSto_K0', 'Fk_PROF10MAJ', 'Fk_PROF10MIN', 'Fk_Prof11MAJ', 'Fk_Prof11MIN', 'Fk_PROF1MAJ',
                          'Fk_PROF1MIN', 'Fk_PROF2MAJ', 'Fk_PROF2MIN', 'Fk_PROF3AMAJ', 'Fk_PROF3AMIN', 'Fk_PROF3AVMAJ',
                          'Fk_PROF3AVMIN', 'Fk_PROF3BMAJ', 'Fk_PROF3BMIN', 'Fk_PROF4MAJ', 'Fk_PROF4MIN', 'Fk_PROF6AMAJ',
                          'Fk_PROF6AMIN', 'Fk_PROF7MAJ', 'Fk_PROF7MIN', 'Fk_PROF8MAJ', 'Fk_PROF8MIN', 'Fk_PROF9MAJ',
                          'Fk_PROF9MIN', 'Fk_PROFSTR1MIN', 'Fk_PROFSTR2MIN'])

    def test_get_duplicated(self):
        self.assertEqual(self.modele.get_duplicated_noeuds(), [])
        self.assertEqual(self.modele.get_duplicated_casiers(), [])
        self.assertEqual(self.modele.get_duplicated_sections(), [])
        self.assertEqual(self.modele.get_duplicated_branches(), [])

    def test_get_theta_preissmann(self):
        self.assertEqual(self.modele.get_theta_preissmann(), 0.75)

    def test_get_branche_barrage(self):
        with self.assertRaises(ExceptionCrue10):
            self.modele.get_branche_barrage()

    def test_get_liste_branches_entre_deux_noeuds(self):
        self.assertEqual([branche.id for branche in self.branches],
                         ['Br_B1', 'Br_B2', 'Br_B3', 'Br_B4'])
        with self.assertRaises(ExceptionCrue10):
            self.modele.get_liste_branches_entre_deux_noeuds('Nd_N5', 'Nd_N1')

    def test_extract_limites_as_dataframe(self):
        basename = 'Etu3-6_limites_Nd_N1-Nd_N5.csv'
        if WRITE_REFERENCE_FILES:
            df_reference = self.modele.extract_limites_as_dataframe(self.branches)
            df_reference.to_csv(os.path.join(FOLDER_IN, basename), sep=CSV_DELIMITER, float_format=FMT_FLOAT_CSV)
        df_actual = self.modele.extract_limites_as_dataframe(self.branches)
        df_actual.to_csv(os.path.join(FOLDER_OUT, basename), sep=CSV_DELIMITER, float_format=FMT_FLOAT_CSV)
        self.assertTrue(cmp(os.path.join(FOLDER_IN, basename), os.path.join(FOLDER_OUT, basename)))
