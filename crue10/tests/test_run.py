import os.path
import unittest

from crue10.tests import DATA_TESTS_FOLDER_ABSPATH
from crue10.etude import Etude


class ResultatsCalculTestCase(unittest.TestCase):

    def setUp(self):
        etude = Etude(os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.2', 'Etu3-6_run', 'Etu3-6.etu.xml'))
        scenario = etude.get_scenario_courant()
        self.run = scenario.get_last_run()

    def test_traces(self):
        self.assertEqual(len(self.run.traces['r']), 30)
        self.assertEqual(len(self.run.traces['g']), 152)
        self.assertEqual(len(self.run.traces['i']), 15)
        self.assertEqual(len(self.run.traces['c']), 24)

    def test_nb(self):
        self.assertEqual(self.run.nb_avertissements(), 0)
        self.assertEqual(self.run.nb_erreurs(), 0)

    def test_get_time(self):
        self.assertEqual(self.run.get_time(), 0.274)
        self.assertEqual(self.run.get_service_time('c'), 0.118)
