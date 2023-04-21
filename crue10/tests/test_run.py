# coding: utf-8
import os.path
import unittest

from crue10.tests import DATA_TESTS_FOLDER_ABSPATH
from crue10.etude import Etude


class ResultatsCalculTestCase(unittest.TestCase):

    def setUp(self):
        etude = Etude(os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.2', 'Etu3-6I_run', 'Etu3-6.etu.xml'))
        scenario = etude.get_scenario_courant()
        self.run_gprec = scenario.get_dernier_run()

        etude = Etude(os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.3', 'Etu3-6I_run', 'Etu3-6.etu.xml'))
        scenario = etude.get_scenario_courant()
        self.run_gcour = scenario.get_dernier_run()

    def test_gprec_traces(self):
        self.assertEqual(len(self.run_gprec.traces['r']), 39)
        self.assertEqual(len(self.run_gprec.traces['g']), 152)
        self.assertEqual(len(self.run_gprec.traces['i']), 15)
        self.assertEqual(len(self.run_gprec.traces['c']), 2274)

    def test_gprec_nb(self):
        self.assertEqual(self.run_gprec.nb_avertissements(), 0)
        self.assertEqual(self.run_gprec.nb_erreurs(), 0)

    def test_gprec_get_time(self):
        self.assertEqual(self.run_gprec.get_time(), 1.383)
        self.assertEqual(self.run_gprec.get_service_time('c'), 1.249)

    def test_gcour_traces(self):
        self.assertEqual(len(self.run_gcour.traces['r']), 39)
        self.assertEqual(len(self.run_gcour.traces['g']), 152)
        self.assertEqual(len(self.run_gcour.traces['i']), 15)
        self.assertEqual(len(self.run_gcour.traces['c']), 2318)

    def test_gcour_nb(self):
        self.assertEqual(self.run_gcour.nb_avertissements(), 41)
        self.assertEqual(self.run_gcour.nb_erreurs(), 0)

    def test_gcour_get_time(self):
        self.assertEqual(self.run_gcour.get_time(), 1.595)
        self.assertEqual(self.run_gcour.get_service_time('c'), 1.396)
