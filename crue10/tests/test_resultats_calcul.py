from collections import OrderedDict
from difflib import unified_diff
from filecmp import cmp
import numpy as np
import os
import pickle
import unittest

from crue10.etude import Etude
from crue10.tests import DATA_TESTS_FOLDER_ABSPATH
from crue10.utils.settings import CSV_DELIMITER


WRITE_FILES = False

FOLDER_IN = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.2', 'Etu3-6I_run')
FOLDER_OUT = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'out', '1.2', 'Etu3-6I_run')

CASIERS = ['Ca_N7', 'Ca_N6']

SECTIONS = ['St_PROF6B', 'St_PROF3AM', 'St_B1_00050', 'St_B1_00150', 'St_B1_00250', 'St_B1_00350', 'St_B1_00450',
            'St_PROF5', 'St_Prof11', 'St_PROF10', 'St_PROF9', 'St_PROF8', 'St_PROF7', 'St_PROF6A', 'St_PROF4',
            'St_PROF3A', 'St_PROF3AV', 'St_PROF3B', 'St_PROF2', 'St_PROF1', 'St_PROFSTR1', 'St_PROFSTR2',
            'St_B5_Am', 'St_B5_Av', 'St_B8_Am', 'St_B8_Av']


def _are_similar_and_print_diff(basename):
    same = True
    with open(os.path.join(FOLDER_IN, basename), 'r') as filein:
        textin = filein.readlines()
    with open(os.path.join(FOLDER_OUT, basename), 'r') as fileout:
        textout = fileout.readlines()
    for line in unified_diff(
            textin, textout,
            fromfile=os.path.join(FOLDER_IN, basename),
            tofile=os.path.join(FOLDER_OUT, basename), lineterm=''):
        print(line)
        same = False
    return same


class ResultatsCalculTestCase(unittest.TestCase):

    def setUp(self):
        etude = Etude(os.path.join(FOLDER_IN, 'Etu3-6.etu.xml'))
        scenario = etude.get_scenario_courant()
        self.sous_modele = scenario.modele.liste_sous_modeles[0]
        self.sous_modele.read_all()
        run = scenario.get_last_run()
        self.resultats = run.get_resultats_calcul()  # ResultatsCalcul
        self.branches = scenario.modele.get_liste_branches_entre_deux_noeuds('Nd_N1', 'Nd_N5')
        self.section_names = [st.id for st in scenario.modele.get_liste_sections()]
        if not os.path.exists(FOLDER_OUT):
            os.makedirs(FOLDER_OUT)

    def test_emh(self):
        self.assertEqual(self.resultats.emh,
                         OrderedDict([('Casier', CASIERS), ('Section', SECTIONS),
                                      ('BrancheSaintVenant', ['Br_B1', 'Br_B2', 'Br_B4']),
                                      ('BrancheStrickler', ['Br_B6'])]))

    def test_variables(self):
        self.assertEqual(self.resultats.variables,
                         OrderedDict([('Noeud', []),
                                      ('Casier', ['Qech', 'Splan', 'Vol']),
                                      ('Section', ['Q', 'Stot', 'Vact', 'Vc', 'Z']),
                                      ('BrancheBarrageFilEau', []),
                                      ('BrancheBarrageGenerique', []),
                                      ('BrancheNiveauxAssocies', []),
                                      ('BrancheOrifice', []),
                                      ('BranchePdc', []),
                                      ('BrancheSaintVenant', ['SplanAct', 'SplanSto', 'SplanTot', 'Vol']),
                                      ('BrancheSeuilLateral', []),
                                      ('BrancheSeuilTransversal', []),
                                      ('BrancheStrickler', ['Splan', 'Vol'])]))

    def test_get_data_pseudoperm(self):
        REFERENCE_FILE_PATH = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'pickle', 'Etu3-6I_run_Cc_P02.p')

        actual = self.resultats.get_data_pseudoperm('Cc_P02')

        if WRITE_FILES:
            with open(REFERENCE_FILE_PATH, 'wb') as f:
                pickle.dump(actual, f)

        with open(REFERENCE_FILE_PATH, 'rb') as f:
            desired = pickle.load(f)
        for key in desired.keys():
            np.testing.assert_equal(actual[key], desired[key])

    def test_get_data_trans(self):
        REFERENCE_FILE_PATH = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'pickle', 'Etu3-6I_run_Cc_T01.p')

        actual = self.resultats.get_data_trans('Cc_T01')

        if WRITE_FILES:
            with open(REFERENCE_FILE_PATH, 'wb') as f:
                pickle.dump(actual, f)

        with open(REFERENCE_FILE_PATH, 'rb') as f:
            desired = pickle.load(f)
        for key in desired.keys():
            np.testing.assert_equal(actual[key], desired[key])

    def test_write_all_calc_pseudoperm_in_csv(self):
        basename = 'Etu3-6I_run_all_pseudoperm.csv'
        if WRITE_FILES:
            self.resultats.write_all_calc_pseudoperm_in_csv(os.path.join(FOLDER_IN, basename))
        self.resultats.write_all_calc_pseudoperm_in_csv(os.path.join(FOLDER_OUT, basename))
        same = _are_similar_and_print_diff(basename)
        self.assertTrue(same)

    def test_write_all_calc_trans_in_csv(self):
        basename = 'Etu3-6I_run_all_trans.csv'
        if WRITE_FILES:
            self.resultats.write_all_calc_trans_in_csv(os.path.join(FOLDER_IN, basename))
        self.resultats.write_all_calc_trans_in_csv(os.path.join(FOLDER_OUT, basename))
        same = _are_similar_and_print_diff(basename)
        self.assertTrue(same)

    def test_extract_profil_long_pseudoperm_as_dataframe(self):
        basename = 'Etu3-6I_run_profil_long_P02.csv'
        if WRITE_FILES:
            df_reference = self.resultats.extract_profil_long_pseudoperm_as_dataframe(
                'Cc_P02', self.branches, ['Z', 'Q'])
            df_reference.to_csv(os.path.join(FOLDER_IN, basename), sep=CSV_DELIMITER)
        df_actual = self.resultats.extract_profil_long_pseudoperm_as_dataframe(
            'Cc_P02', self.branches, ['Z', 'Q'])
        df_actual.to_csv(os.path.join(FOLDER_OUT, basename), sep=CSV_DELIMITER)
        self.assertTrue(cmp(os.path.join(FOLDER_IN, basename), os.path.join(FOLDER_OUT, basename)))

    def test_extract_profil_long_trans_at_time_as_dataframe(self):
        basename = 'Etu3-6I_run_profil_long_T01_6h.csv'
        if WRITE_FILES:
            df_reference = self.resultats.extract_profil_long_trans_at_time_as_dataframe('Cc_T01', self.branches, 6)
            df_reference.to_csv(os.path.join(FOLDER_IN, basename), sep=CSV_DELIMITER)
        df_actual = self.resultats.extract_profil_long_trans_at_time_as_dataframe('Cc_T01', self.branches, 6)
        df_actual.to_csv(os.path.join(FOLDER_OUT, basename), sep=CSV_DELIMITER)
        self.assertTrue(cmp(os.path.join(FOLDER_IN, basename), os.path.join(FOLDER_OUT, basename)))

    def test_extract_profil_long_trans_max_as_dataframe(self):
        basename = 'Etu3-6I_run_profil_long_T01_max.csv'
        if WRITE_FILES:
            df_reference = self.resultats.extract_profil_long_trans_max_as_dataframe('Cc_T01', self.branches)
            df_reference.to_csv(os.path.join(FOLDER_IN, basename), sep=CSV_DELIMITER)
        df_actual = self.resultats.extract_profil_long_trans_max_as_dataframe('Cc_T01', self.branches)
        df_actual.to_csv(os.path.join(FOLDER_OUT, basename), sep=CSV_DELIMITER)
        self.assertTrue(cmp(os.path.join(FOLDER_IN, basename), os.path.join(FOLDER_OUT, basename)))

    def test_get_all_pseudoperm_var_at_emhs_as_array(self):
        REFERENCE_FILE_PATH = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'pickle', 'Etu3-6I_run_pseudoperm_Z_at_sections.p')

        actual = self.resultats.get_all_pseudoperm_var_at_emhs_as_array('Z', self.section_names)

        if WRITE_FILES:
            with open(REFERENCE_FILE_PATH, 'wb') as f:
                pickle.dump(actual, f)

        with open(REFERENCE_FILE_PATH, 'rb') as f:
            desired = pickle.load(f)
        np.testing.assert_equal(actual, desired)

    def test_get_trans_var_at_emhs_as_array(self):
        REFERENCE_FILE_PATH = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'pickle', 'Etu3-6I_run_trans_T01_Z_at_sections.p')

        actual = self.resultats.get_trans_var_at_emhs_as_array('Cc_T01', 'Z', self.section_names)

        if WRITE_FILES:
            with open(REFERENCE_FILE_PATH, 'wb') as f:
                pickle.dump(actual, f)

        with open(REFERENCE_FILE_PATH, 'rb') as f:
            desired = pickle.load(f)
        np.testing.assert_equal(actual, desired)
