import copy
import numpy as np
import os.path
import unittest

from crue10.etude import Etude
from crue10.emh.section import DEFAULT_FK_STO_ID, DEFAULT_FK_MAJ_ID, DEFAULT_FK_MIN_ID, \
    LimiteGeom, SectionProfil
from crue10.sous_modele import SousModele
from crue10.tests import DATA_TESTS_FOLDER_ABSPATH
from crue10.utils import ExceptionCrue10


class SousModeleTestCase(unittest.TestCase):

    def setUp(self):
        etude = Etude(os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.2', 'Etu3-6', 'Etu3-6.etu.xml'))
        self.sous_modele = etude.get_sous_modele('Sm_M3-6_c10')
        self.sous_modele.read_all(ignore_shp=True)

    def _test_rename_emhs(self, sous_modele):
        SUFFIXE = '_new'

        def iter_on_lois_frottement_in_sectionprofils():
            for section in sous_modele.get_liste_sections_profil():
                for lit in section.lits_numerotes:
                    yield lit.loi_frottement.id

        lois_frottement_ids = copy.deepcopy(list(sous_modele.lois_frottement.keys()))
        lois_frottement_in_sections_ori = list(iter_on_lois_frottement_in_sectionprofils())

        sous_modele.rename_emhs(SUFFIXE, emh_list=['Fk'])

        lois_frottement_in_sections_new = list(iter_on_lois_frottement_in_sectionprofils())

        self.assertEqual([nom_loi + SUFFIXE for nom_loi in lois_frottement_ids],
                         list(sous_modele.lois_frottement.keys()))
        self.assertEqual([nom_loi + SUFFIXE for nom_loi in lois_frottement_in_sections_ori],
                         lois_frottement_in_sections_new)

    def test_summary(self):
        self.assertEqual(self.sous_modele.summary(), "Sous-modèle Sm_M3-6_c10: 7 noeuds, 7 branches, 26 sections (14 profils, 2 idems, 6 interpolées, 4 sans géométrie), 2 casiers (3 profils casier)")

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

    def test_rename_emhs(self):
        self._test_rename_emhs(self.sous_modele)

    def test_rename_emhs_from_scratch(self):
        sous_modele = SousModele("Sm_from_sratch", mode='w')
        sous_modele.ajouter_lois_frottement_par_defaut()

        section = SectionProfil("St_from_scratch")

        largeur_sto_d = 60.0
        largeur_maj_d = 40.0
        largeur_min = 500.0
        largeur_maj_g = 40.0
        largeur_sto_g = 60.0

        z_rive = 10.0
        z_sto_maj = 8.0
        z_maj_min = 4.0
        z_thalweg = 0.0

        xt_initial = -10.0  # Borne RD Bathy à xt=0

        xz = np.array([
            (xt_initial, z_rive),
            (largeur_sto_d, z_sto_maj),
            (largeur_maj_d, z_maj_min),
            (largeur_min / 2, z_thalweg),  # Centered thalweg
            (largeur_min / 2, z_maj_min),
            (largeur_maj_g, z_sto_maj),
            (largeur_sto_g, z_rive)
        ])
        xz[:, 0] = xz[:, 0].cumsum()

        xt_limites = np.array([
            xt_initial,
            largeur_sto_d,
            largeur_maj_d,
            largeur_min,
            largeur_maj_g,
            largeur_sto_g,
        ])
        xt_limites = xt_limites.cumsum()

        section.set_xz(xz)
        xt_axe_hydraulique = xt_initial + largeur_sto_d + largeur_maj_d + largeur_min / 2
        section.ajouter_limite_geom(LimiteGeom(LimiteGeom.AXE_HYDRAULIQUE, xt_axe_hydraulique))
        xt_thalweg = xt_initial + largeur_sto_d + largeur_maj_d + largeur_min / 2
        section.ajouter_limite_geom(LimiteGeom(LimiteGeom.THALWEG, xt_thalweg))

        loi_sto = sous_modele.get_loi_frottement(DEFAULT_FK_STO_ID)
        loi_maj = sous_modele.get_loi_frottement(DEFAULT_FK_MAJ_ID)
        loi_min = sous_modele.get_loi_frottement(DEFAULT_FK_MIN_ID)
        section.set_lits_numerotes(xt_limites, [
            loi_sto,
            loi_maj,
            loi_min,
            loi_maj,
            loi_sto,
        ])

        sous_modele.ajouter_section(section)

        self._test_rename_emhs(sous_modele)
