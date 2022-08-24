import numpy as np
import os.path
import unittest

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10


class SousModeleTestCase(unittest.TestCase):

    def setUp(self):
        etude = Etude(os.path.join('crue10', 'tests', 'data', 'in', '1.2', 'Etu3-6', 'Etu3-6.etu.xml'))
        self.sous_modele = etude.get_sous_modele('Sm_M3-6_c10')
        self.sous_modele.read_all(ignore_shp=True)

    def test_get(self):
        # Noeud
        self.assertEqual(self.sous_modele.get_noeud('Nd_N1').id, 'Nd_N1')

        # Casier
        casier = self.sous_modele.get_casier('Ca_N7')
        self.assertEqual(casier.id, 'Ca_N7')
        self.assertEqual(casier.geom, None)

        # ProfilCasier
        profil_casier = casier.profils_casier[0]
        self.assertEqual(profil_casier.id, 'Pc_N7_001')
        self.assertEqual(profil_casier.longueur, 200.0)
        self.assertTrue((profil_casier.xz == np.array([(0, 0.2), (100, 0.2)])).all())

    def test_get_liste(self):
        self.assertEqual([noeud.id for noeud in self.sous_modele.get_liste_noeuds()],
                         ['Nd_N1', 'Nd_N2', 'Nd_N6', 'Nd_N3', 'Nd_N4', 'Nd_N7', 'Nd_N5'])
        self.assertEqual([casier.id for casier in self.sous_modele.get_liste_casiers()],
                         ['Ca_N7', 'Ca_N6'])
        self.assertEqual([section.id for section in self.sous_modele.get_liste_sections()],
                         ['St_Prof11', 'St_B1_00050', 'St_PROF10', 'St_B1_00150', 'St_PROF9', 'St_B1_00250',
                          'St_PROF8', 'St_B1_00350', 'St_PROF7', 'St_B1_00450', 'St_PROF6A', 'St_PROF6B', 'St_PROF5',
                          'St_PROF4', 'St_PROF3A', 'St_PROF3AM', 'St_PROF3AV', 'St_PROF3B', 'St_PROF2', 'St_PROF1',
                          'St_PROFSTR1', 'St_PROFSTR2', 'St_B5_Am', 'St_B5_Av', 'St_B8_Am', 'St_B8_Av'])
        self.assertEqual([section.id for section in self.sous_modele.get_liste_sections_profil()],
                         ['St_Prof11', 'St_PROF10', 'St_PROF9', 'St_PROF8', 'St_PROF7', 'St_PROF6A', 'St_PROF4',
                          'St_PROF3A', 'St_PROF3AV', 'St_PROF3B', 'St_PROF2', 'St_PROF1', 'St_PROFSTR1', 'St_PROFSTR2'])
        self.assertEqual([branche.id for branche in self.sous_modele.get_liste_branches()],
                         ['Br_B1', 'Br_B2', 'Br_B3', 'Br_B4', 'Br_B6', 'Br_B5', 'Br_B8'])
        self.assertEqual([loi.id for loi in self.sous_modele.get_liste_lois_frottement()],
                         ['FkSto_K0', 'Fk_PROF10MAJ', 'Fk_PROF10MIN', 'Fk_Prof11MAJ', 'Fk_Prof11MIN', 'Fk_PROF1MAJ',
                          'Fk_PROF1MIN', 'Fk_PROF2MAJ', 'Fk_PROF2MIN', 'Fk_PROF3AMAJ', 'Fk_PROF3AMIN', 'Fk_PROF3AVMAJ',
                          'Fk_PROF3AVMIN', 'Fk_PROF3BMAJ', 'Fk_PROF3BMIN', 'Fk_PROF4MAJ', 'Fk_PROF4MIN', 'Fk_PROF6AMAJ',
                          'Fk_PROF6AMIN', 'Fk_PROF7MAJ', 'Fk_PROF7MIN', 'Fk_PROF8MAJ', 'Fk_PROF8MIN', 'Fk_PROF9MAJ',
                          'Fk_PROF9MIN', 'Fk_PROFSTR1MIN', 'Fk_PROFSTR2MIN'])

    def test_get_connected_branches(self):
        self.assertEqual([branche.id for branche in self.sous_modele.get_connected_branches_in('Nd_N2')],
                         ['Br_B1'])
        self.assertEqual([branche.id for branche in self.sous_modele.get_connected_branches_out('Nd_N2')],
                         ['Br_B2', 'Br_B5'])
        self.assertEqual([branche.id for branche in self.sous_modele.get_connected_branches('Nd_N2')],
                         ['Br_B1', 'Br_B2', 'Br_B5'])

    def test_get_connected_casier(self):
        self.assertEqual(self.sous_modele.get_connected_casier(self.sous_modele.get_noeud('Nd_N7')),
                         self.sous_modele.get_casier('Ca_N7'))

    def test_are_sections_similar(self):
        section1 = self.sous_modele.get_section('St_PROF6A')
        section2 = self.sous_modele.get_section('St_PROF6B')
        section3 = self.sous_modele.get_section('St_PROF7')
        self.assertTrue(self.sous_modele.are_sections_similar(section1, section2))
        self.assertTrue(self.sous_modele.are_sections_similar(section2, section1))
        self.assertFalse(self.sous_modele.are_sections_similar(section1, section3))
        self.assertFalse(self.sous_modele.are_sections_similar(section3, section1))

    def test_decouper_branche_fluviale_and_is_noeud_supprimable_and_supprimer_noeud_entre_deux_branches_fluviales(self):
        # decouper_branche_fluviale
        self.sous_modele.decouper_branche_fluviale('Br_B1', 'Br_BX', 'St_PROF8', 'Nd_NX')
        with self.assertRaises(ExceptionCrue10):
            self.sous_modele.decouper_branche_fluviale('Br_B1', 'Br_BX', 'St_Prof11', 'Nd_NX')
            self.sous_modele.decouper_branche_fluviale('Br_B1', 'Br_BX', 'St_B1_00250', 'Nd_NX')

        # is_noeud_supprimable
        self.assertFalse(self.sous_modele.is_noeud_supprimable(self.sous_modele.get_noeud('Nd_N2')))
        self.assertTrue(self.sous_modele.is_noeud_supprimable(self.sous_modele.get_noeud('Nd_NX')))

        # supprimer_noeud_entre_deux_branches_fluviales
        self.sous_modele.supprimer_noeud_entre_deux_branches_fluviales(self.sous_modele.get_noeud('Nd_NX'))
        with self.assertRaises(ExceptionCrue10):
            self.sous_modele.supprimer_noeud_entre_deux_branches_fluviales(self.sous_modele.get_noeud('Nd_N2'))

    def test_remove_sectioninterpolee(self):
        self.sous_modele.remove_sectioninterpolee()
        self.assertEqual(len(self.sous_modele.get_liste_sections_interpolees()), 0)
