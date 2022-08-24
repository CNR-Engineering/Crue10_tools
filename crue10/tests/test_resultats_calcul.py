from collections import OrderedDict
import numpy as np
import os.path
import pickle
import unittest

from crue10.tests import DATA_TESTS_FOLDER_ABSPATH
from crue10.etude import Etude


WRITE_PICKLE_FILES = False

CASIERS = ['Ca_N7', 'Ca_N6']

SECTIONS = ['St_PROF6B', 'St_PROF3AM', 'St_B1_00050', 'St_B1_00150', 'St_B1_00250', 'St_B1_00350', 'St_B1_00450',
            'St_PROF5', 'St_Prof11', 'St_PROF10', 'St_PROF9', 'St_PROF8', 'St_PROF7', 'St_PROF6A', 'St_PROF4',
            'St_PROF3A', 'St_PROF3AV', 'St_PROF3B', 'St_PROF2', 'St_PROF1', 'St_PROFSTR1', 'St_PROFSTR2',
            'St_B5_Am', 'St_B5_Av', 'St_B8_Am', 'St_B8_Av']


class ResultatsCalculTestCase(unittest.TestCase):

    def setUp(self):
        etude = Etude(os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.2', 'Etu3-6_run', 'Etu3-6.etu.xml'))
        scenario = etude.get_scenario_courant()
        self.sous_modele = scenario.modele.liste_sous_modeles[0]
        self.sous_modele.read_all()
        run = scenario.get_last_run()
        self.resultats = run.get_resultats_calcul()

    def test_emh(self):
        self.assertEqual(self.resultats.emh,
                         OrderedDict([('Casier', CASIERS), ('Section', SECTIONS),
                                      ('BrancheSaintVenant', ['Br_B1', 'Br_B2', 'Br_B4']),
                                      ('BrancheStrickler', ['Br_B6'])]))

    def test_variables(self):
        print(self.resultats.variables)
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

    def test_get_res_calc_pseudoperm(self):
        res = self.resultats.get_res_calc_pseudoperm('Cc_P02')
        self.assertEqual(res.name, 'Cc_P02')

    def test_res(self):
        REFERENCE_FILE_PATH = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'pickle', 'Etu3-6_run_Cc_P02.p')

        actual = self.resultats.get_res_steady('Cc_P02')

        if WRITE_PICKLE_FILES:
            with open(REFERENCE_FILE_PATH, 'wb') as f:
                pickle.dump(actual, f)

        with open(REFERENCE_FILE_PATH, 'rb') as f:
            desired = pickle.load(f)
        for key in desired.keys():
            np.testing.assert_equal(actual[key], desired[key])
