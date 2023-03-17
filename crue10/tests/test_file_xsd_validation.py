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
        with self.assertLogs(level='INFO') as cm:
            self.etude_etu3_6.log_check_xml(self.etude_etu3_6.folder)
            self.assertEqual(cm.output, [
                'INFO:crue10.utils:=> Aucune erreur dans les fichiers XML (pour Étude Etu3-6)'
            ])

    def test_etu_ko(self):
        with self.assertRaises(ExceptionCrue10):
            Etude(os.path.join('crue10', 'tests', 'data', 'in', '1.3', 'Etu3-6_XML-errors', 'Etu3-6_KO.etu.xml'))

    def test_etu_validation(self):
        with self.assertLogs(level='INFO') as cm:
            self.etude_etu3_6_xml_errors.log_check_xml(self.etude_etu3_6_xml_errors.folder)
            self.assertEqual('\n'.join(cm.output), """ERROR:crue10.utils:~> 1 erreur(s) dans M3-6_c10_ko.ocal.xml:
ERROR:crue10.utils:    #1: Error XML: file is probably not well-formed or corrupted
ERROR:crue10.utils:~> 1 erreur(s) dans M3-6_c10_ko.ores.xml:
ERROR:crue10.utils:    #1: Invalid XML at line 17: cvc-complex-type.2.4.a: Invalid content was found starting with element '{"http://www.fudaa.fr/xsd/crue":OrdResNoeuds_UNEXPECTED}'. One of '{"http://www.fudaa.fr/xsd/crue":OrdResNoeuds}' is expected.
ERROR:crue10.utils:~> 2 erreur(s) dans M3-6_c10.drso.xml:
ERROR:crue10.utils:    #1: Invalid XML at line 12: cvc-id.2: There are multiple occurrences of ID value 'Nd_N1'.
ERROR:crue10.utils:    #2: Invalid XML at line 12: cvc-attribute.3: The value 'Nd_N1' of attribute 'Nom' on element 'NoeudNiveauContinu' is not valid with respect to its type, 'TypeForAttributeNomNoeud'.
ERROR:crue10.utils:~> 1 erreur(s) dans M3-6_c10.opti.xml:
ERROR:crue10.utils:    #1: Invalid XML at line 4: cvc-complex-type.2.4.a: Invalid content was found starting with element '{"http://www.fudaa.fr/xsd/crue":Sorties_UNEXPECTED}'. One of '{"http://www.fudaa.fr/xsd/crue":Sorties}' is expected.
ERROR:crue10.utils:=> 5 erreur(s) dans les fichiers XML""")
