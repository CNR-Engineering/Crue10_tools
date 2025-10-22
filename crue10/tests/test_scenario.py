import logging
import os.path
import unittest

from crue10.etude import Etude
from crue10.tests import DATA_TESTS_FOLDER_ABSPATH
from crue10.utils import logger


class ScenarioTestCase(unittest.TestCase):

    def setUp(self):
        self.etude_etu3_6 = Etude(os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.3', 'Etu3-6', 'Etu3-6.etu.xml'))
        self.scenario_etu3_6 = self.etude_etu3_6.get_scenario_courant()
        self.scenario_etu3_6.read_all()

        self.etude_etu3_6_xml_errors = Etude(os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.3', 'Etu3-6_XML-errors',
                                                          'Etu3-6.etu.xml'))
        #self.etude_etu3_6_xml_errors.read_all()
        self.scenario_etu3_6_xml_errors = self.etude_etu3_6_xml_errors.get_scenario('Sc_M3-6_c10')
        self.scenario_ko_etu3_6_xml_errors = self.etude_etu3_6_xml_errors.get_scenario('Sc_M3-6_c10_ko')
        #self.scenario_ko_etu3_6_xml_errors.read_all()

        self.etude_from_scratch = Etude(os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.3', 'Etu_from_scratch',
                                                     'Etu_from_scratch.etu.xml'))
        self.scenario_from_scratch = self.etude_from_scratch.get_scenario_courant()
        self.scenario_from_scratch.read_all()

        self.etude_etu3_6i_run = Etude(os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', '1.2', 'Etu3-6I_run',
                                                    'Etu3-6.etu.xml'))
        self.scenario_etu3_6i_run = self.etude_etu3_6i_run.get_scenario_courant()
        self.scenario_etu3_6i_run.read_all()

    def test_summary(self):
        self.assertEqual(self.scenario_etu3_6.summary(), "Scénario Sc_M3-6_c10: Mo_M3-6_c10 (2 calculs, dont 2 pseudo-permanents et 0 transitoire actifs)")
        self.assertEqual(self.scenario_etu3_6_xml_errors.summary(), "Scénario Sc_M3-6_c10: Mo_M3-6_c10 (0 calcul, dont 0 pseudo-permanent et 0 transitoire actif)")
        self.assertEqual(self.scenario_ko_etu3_6_xml_errors.summary(), "Scénario Sc_M3-6_c10_ko: Mo_M3-6_c10 (0 calcul, dont 0 pseudo-permanent et 0 transitoire actif)")
        self.assertEqual(self.scenario_from_scratch.summary(), "Scénario Sc_mono_sm_avec_bgefileau: Mo_mono_sm_avec_bgefileau (0 calcul, dont 0 pseudo-permanent et 0 transitoire actif)")
        self.assertEqual(self.scenario_etu3_6i_run.summary(), "Scénario Sc_M3-6I_c10: Mo_M3-6I_c10 (3 calculs, dont 2 pseudo-permanents et 1 transitoire actifs)")

    def test_check_xml_scenario_etu3_6(self):
        errors_list = self.scenario_etu3_6.check_xml_scenario(self.etude_etu3_6.folder)
        self.assertListEqual(errors_list, [])

    def test_check_xml_scenario_etu3_6_xml_errors(self):
        errors = self.scenario_etu3_6_xml_errors.check_xml_scenario(self.etude_etu3_6_xml_errors.folder)
        self.assertListEqual(errors, [
            "Invalid XML at line 3585: Element '{http://www.fudaa.fr/xsd/crue}Sorties_UNEXPECTED': This element is not expected. Expected is ( {http://www.fudaa.fr/xsd/crue}Sorties ).",
            "Invalid XML at line 3720: Element '{http://www.fudaa.fr/xsd/crue}NoeudNiveauContinu': Duplicate key-sequence ['Nd_N1'] in key identity-constraint '{http://www.fudaa.fr/xsd/crue}PK_Noeud'."
        ])

    def test_check_xml_scenario_ko_etu3_6_xml_errors(self):
        errors = self.scenario_ko_etu3_6_xml_errors.check_xml_scenario(self.etude_etu3_6_xml_errors.folder)
        self.assertListEqual(errors, [
            "Invalid XML at line 3343: Element '{http://www.fudaa.fr/xsd/crue}Avancement_CRASH': This element is not expected. Expected is ( {http://www.fudaa.fr/xsd/crue}Avancement ).",
            "Invalid XML at line 3372: Element '{http://www.fudaa.fr/xsd/crue}OrdResNoeuds_UNEXPECTED': This element is not expected. Expected is ( {http://www.fudaa.fr/xsd/crue}OrdResNoeuds ).",
            "Invalid XML at line 3554: Element '{http://www.fudaa.fr/xsd/crue}Sorties_UNEXPECTED': This element is not expected. Expected is ( {http://www.fudaa.fr/xsd/crue}Sorties ).",
            "Invalid XML at line 3689: Element '{http://www.fudaa.fr/xsd/crue}NoeudNiveauContinu': Duplicate key-sequence ['Nd_N1'] in key identity-constraint '{http://www.fudaa.fr/xsd/crue}PK_Noeud'.",
        ])

    def test_check_xml_scenario_etu_from_scratch(self):
        errors_list = self.scenario_from_scratch.check_xml_scenario(self.etude_from_scratch.folder)
        self.assertListEqual(errors_list, [])

    def test_log_check_xml_scenario_etu3_6(self):
        with self.assertLogs(logger=logger, level=logging.INFO) as log:
            self.scenario_etu3_6.log_check_xml_scenario(self.etude_etu3_6.folder)
            self.assertEqual(log.output, [
                "INFO:crue10.utils:=> Aucune erreur dans le scénario Scénario Sc_M3-6_c10",
            ])

    def test_log_check_xml_scenario_etu3_6_xml_errors(self):
        with self.assertLogs(logger=logger, level=logging.INFO) as log:
            self.scenario_etu3_6_xml_errors.log_check_xml_scenario(self.etude_etu3_6_xml_errors.folder)
            self.assertEqual(log.output, [
                "ERROR:crue10.utils:    #1: Invalid XML at line 3585: Element '{http://www.fudaa.fr/xsd/crue}Sorties_UNEXPECTED': This element is not expected. Expected is ( {http://www.fudaa.fr/xsd/crue}Sorties ).",
                "ERROR:crue10.utils:    #2: Invalid XML at line 3720: Element '{http://www.fudaa.fr/xsd/crue}NoeudNiveauContinu': Duplicate key-sequence ['Nd_N1'] in key identity-constraint '{http://www.fudaa.fr/xsd/crue}PK_Noeud'.",
                "ERROR:crue10.utils:=> 2 erreurs dans le scénario Scénario Sc_M3-6_c10",
            ])

    def test_log_check_xml_scenario_ko_etu3_6_xml_errors(self):
        with self.assertLogs(logger=logger, level=logging.INFO) as log:
            self.scenario_ko_etu3_6_xml_errors.log_check_xml_scenario(self.etude_etu3_6_xml_errors.folder)
            self.assertEqual(log.output, [
                "ERROR:crue10.utils:    #1: Invalid XML at line 3343: Element '{http://www.fudaa.fr/xsd/crue}Avancement_CRASH': This element is not expected. Expected is ( {http://www.fudaa.fr/xsd/crue}Avancement ).",
                "ERROR:crue10.utils:    #2: Invalid XML at line 3372: Element '{http://www.fudaa.fr/xsd/crue}OrdResNoeuds_UNEXPECTED': This element is not expected. Expected is ( {http://www.fudaa.fr/xsd/crue}OrdResNoeuds ).",
                "ERROR:crue10.utils:    #3: Invalid XML at line 3554: Element '{http://www.fudaa.fr/xsd/crue}Sorties_UNEXPECTED': This element is not expected. Expected is ( {http://www.fudaa.fr/xsd/crue}Sorties ).", "ERROR:crue10.utils:    #4: Invalid XML at line 3689: Element '{http://www.fudaa.fr/xsd/crue}NoeudNiveauContinu': Duplicate key-sequence ['Nd_N1'] in key identity-constraint '{http://www.fudaa.fr/xsd/crue}PK_Noeud'.",
                "ERROR:crue10.utils:=> 4 erreurs dans le scénario Scénario Sc_M3-6_c10_ko"
            ])

    def test_log_check_xml_scenario_etu_from_scratch(self):
        with self.assertLogs(logger=logger, level=logging.INFO) as log:
            self.scenario_from_scratch.log_check_xml_scenario(self.etude_from_scratch.folder)
            self.assertEqual(log.output, [
                'INFO:crue10.utils:=> Aucune erreur dans le scénario Scénario Sc_mono_sm_avec_bgefileau',
            ])
