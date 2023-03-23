"""
Remark: validation of a whole scenario is done in `test_scenario.py`.
"""
from logging import INFO
import os.path
import unittest

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger


logger.setLevel(INFO)


class ScenarioTestCase(unittest.TestCase):

    def setUp(self):
        self.etude_etu3_6 = Etude(os.path.join('crue10', 'tests', 'data', 'in', '1.3', 'Etu3-6', 'Etu3-6.etu.xml'))
        self.etude_etu3_6_xml_errors = Etude(os.path.join('crue10', 'tests', 'data', 'in', '1.3',
                                                          'Etu3-6_XML-errors', 'Etu3-6.etu.xml'))
        self.etude_from_scratch = Etude(os.path.join('crue10', 'tests', 'data', 'in', '1.3', 'Etu_from_scratch',
                                                     'Etu_from_scratch.etu.xml'))

    def test_etu_ok(self):
        errors = self.etude_etu3_6.check_xml_files(self.etude_etu3_6.folder)
        self.assertEqual(errors, {
            'Etu3-6.etu.xml': [],
            'M3-6_c10.dclm.xml': [],
            'M3-6_c10.dcsp.xml': [],
            'M3-6_c10.dfrt.xml': [],
            'M3-6_c10.dlhy.xml': [],
            'M3-6_c10.dptg.xml': [],
            'M3-6_c10.dpti.xml': [],
            'M3-6_c10.dreg.xml': [],
            'M3-6_c10.drso.xml': [],
            'M3-6_c10.ocal.xml': [],
            'M3-6_c10.optg.xml': [],
            'M3-6_c10.opti.xml': [],
            'M3-6_c10.optr.xml': [],
            'M3-6_c10.ores.xml': [],
            'M3-6_c10.pcal.xml': [],
            'M3-6_c10.pnum.xml': [],
        })

    def test_etu_ko(self):
        with self.assertRaises(ExceptionCrue10):
            Etude(os.path.join('crue10', 'tests', 'data', 'in', '1.3', 'Etu3-6_XML-errors', 'Etu3-6_KO.etu.xml'))

    def test_etu_validation(self):
        errors = self.etude_etu3_6_xml_errors.check_xml_files(self.etude_etu3_6_xml_errors.folder)
        self.assertEqual(errors, {
            'Etu3-6.etu.xml': [],
            'M3-6_c10_ko.dclm.xml': [],
            'M3-6_c10_ko.dlhy.xml': [],
            'M3-6_c10_ko.ocal.xml': [
                "Invalid XML at line 15: Element '{http://www.fudaa.fr/xsd/crue}Avancement_CRASH': This element is not expected. Expected is ( {http://www.fudaa.fr/xsd/crue}Avancement )."
            ],
            'M3-6_c10_ko.ores.xml': [
                "Invalid XML at line 33: Element '{http://www.fudaa.fr/xsd/crue}OrdResNoeuds_UNEXPECTED': This element is not expected. Expected is ( {http://www.fudaa.fr/xsd/crue}OrdResNoeuds )."
            ],
            'M3-6_c10_ko.pcal.xml': [],
            'M3-6_c10.dclm.xml': [],
            'M3-6_c10.dcsp.xml': [],
            'M3-6_c10.dfrt.xml': [],
            'M3-6_c10.dlhy.xml': [],
            'M3-6_c10.dptg.xml': [],
            'M3-6_c10.dpti.xml': [],
            'M3-6_c10.dreg.xml': [],
            'M3-6_c10.drso.xml': [
                "Invalid XML at line 23: Element '{http://www.fudaa.fr/xsd/crue}NoeudNiveauContinu', attribute 'Nom': 'Nd_N1' is not a valid value of the atomic type '{http://www.fudaa.fr/xsd/crue}TypeForAttributeNomNoeud'.",
                "Invalid XML at line 23: Element '{http://www.fudaa.fr/xsd/crue}NoeudNiveauContinu', attribute 'Nom': Warning: No precomputed value available, the value was either invalid or something strange happened.",
                "Invalid XML at line 23: Element '{http://www.fudaa.fr/xsd/crue}NoeudNiveauContinu': Not all fields of key identity-constraint '{http://www.fudaa.fr/xsd/crue}PK_Noeud' evaluate to a node."
            ],
            'M3-6_c10.ocal.xml': [],
            'M3-6_c10.optg.xml': [],
            'M3-6_c10.opti.xml': [
                "Invalid XML at line 7: Element '{http://www.fudaa.fr/xsd/crue}Sorties_UNEXPECTED': This element is not expected. Expected is ( {http://www.fudaa.fr/xsd/crue}Sorties )."
            ],
            'M3-6_c10.optr.xml': [],
            'M3-6_c10.ores.xml': [],
            'M3-6_c10.pcal.xml': [],
            'M3-6_c10.pnum.xml': []
        })
