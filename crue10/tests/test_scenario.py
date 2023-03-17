from lxml.etree import XIncludeError
import os.path
import unittest

from crue10.etude import Etude


class ScenarioTestCase(unittest.TestCase):

    def setUp(self):
        self.etude_etu3_6 = Etude(os.path.join('crue10', 'tests', 'data', 'in', '1.3', 'Etu3-6', 'Etu3-6.etu.xml'))
        self.etude_etu3_6_xml_errors = Etude(os.path.join('crue10', 'tests', 'data', 'in', '1.3', 'Etu3-6_XML-errors',
                                                          'Etu3-6.etu.xml'))
        self.etude_from_scratch = Etude(os.path.join('crue10', 'tests', 'data', 'in', '1.3', 'Etu_from_scratch',
                                                     'Etu_from_scratch.etu.xml'))

    def test_check_xml_scenario_etu3_6(self):
        scenario = self.etude_etu3_6.get_scenario_courant()
        errors_list = scenario.check_xml_scenario(self.etude_etu3_6.folder)
        self.assertListEqual(errors_list, [])

    def test_check_xml_scenario_etu3_6_xml_errors(self):
        scenario = self.etude_etu3_6_xml_errors.get_scenario('Sc_M3-6_c10')
        errors_list = scenario.check_xml_scenario(self.etude_etu3_6_xml_errors.folder)
        self.assertListEqual(errors_list, [
            """Invalid XML at line 3581: cvc-complex-type.2.4.a: Invalid content was found starting with element '{"http://www.fudaa.fr/xsd/crue":Sorties_UNEXPECTED}'. One of '{"http://www.fudaa.fr/xsd/crue":Sorties}' is expected.""",
        ])

        scenario = self.etude_etu3_6_xml_errors.get_scenario('Sc_M3-6_c10_ko')
        with self.assertRaises(XIncludeError):
            scenario.check_xml_scenario(self.etude_etu3_6_xml_errors.folder)

    def test_check_xml_scenario_etu_from_scratch(self):
        scenario = self.etude_from_scratch.get_scenario_courant()
        errors_list = scenario.check_xml_scenario(self.etude_from_scratch.folder)
        self.assertListEqual(errors_list, [])
