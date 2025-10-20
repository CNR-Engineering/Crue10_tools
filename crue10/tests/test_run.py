import os.path
import unittest

from crue10.etude import Etude
from crue10.tests import DATA_TESTS_FOLDER_ABSPATH


class RunGprecTestCase(unittest.TestCase):

    def setUp(self):
        etude = Etude(os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.2', 'Etu3-6I_run', 'Etu3-6.etu.xml'))
        scenario = etude.get_scenario_courant()
        self.run = scenario.get_dernier_run()

    def test_repr(self):
        self.assertEqual(str(self.run), "Run R2023-04-17-10h07m24s (0 avertissement + 0 erreur au total, 0 avertissement + 0 erreur de calcul)")

    def test_gprec_traces(self):
        self.assertEqual(len(self.run.traces['r']), 39)
        self.assertEqual(len(self.run.traces['g']), 152)
        self.assertEqual(len(self.run.traces['i']), 15)
        self.assertEqual(len(self.run.traces['c']), 2274)

    def test_gprec_nb(self):
        self.assertEqual(self.run.nb_avertissements(), 0)
        self.assertEqual(self.run.nb_erreurs(), 0)

    def test_gprec_get_time(self):
        self.assertEqual(self.run.get_time(), 1.383)
        self.assertEqual(self.run.get_service_time('c'), 1.249)


class RunGcourTestCase(unittest.TestCase):

    def setUp(self):
        etude = Etude(os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.3', 'Etu3-6I_run', 'Etu3-6.etu.xml'))
        scenario = etude.get_scenario_courant()
        self.run = scenario.get_dernier_run()

    def test_repr(self):
        self.assertEqual(str(self.run), "Run R2023-04-21-15h39m47s (41 avertissements + 0 erreur au total, 41 avertissements + 0 erreur de calcul)")

    def test_gcour_traces(self):
        self.assertEqual(len(self.run.traces['r']), 39)
        self.assertEqual(len(self.run.traces['g']), 152)
        self.assertEqual(len(self.run.traces['i']), 15)
        self.assertEqual(len(self.run.traces['c']), 2318)

    def test_gcour_nb(self):
        self.assertEqual(self.run.nb_avertissements(), 41)
        self.assertEqual(self.run.nb_erreurs(), 0)

    def test_gcour_get_time(self):
        self.assertEqual(self.run.get_time(), 1.595)
        self.assertEqual(self.run.get_service_time('c'), 1.396)
