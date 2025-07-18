# coding: utf-8
import os.path
import unittest

from crue10.campagne_otfa import FichierOtfa
from crue10.utils.settings import VERSION_GRAMMAIRE_COURANTE
from . import WRITE_REFERENCE_FILES


class FichierOtfaTestCase(unittest.TestCase):

    def setUp(self):
        self.fichierotfa = FichierOtfa(
            'Cas-tests_Etu3-5',
            files={'otfa': os.path.join('crue10', 'tests', 'data', 'in', VERSION_GRAMMAIRE_COURANTE, 'otfa',
                                        'Cas-tests_Etu3-5.otfa.xml')},
        )
        self.fichierotfa.read_otfa()

    def test_fichierotfa(self):
        self.assertEqual(len(self.fichierotfa.campagnes), 5)

        campagne = self.fichierotfa.campagnes[0]
        self.assertEqual(campagne.chemin_etude_ref, "Etu3-5\\Etu3-5.etu.xml")
        self.assertEqual(campagne.nom_scenario_ref, "Sc_M3-5_c10")
        self.assertEqual(campagne.chemin_etude_cible, "Etu3-5\\Etu3-5.etu.xml")
        self.assertEqual(campagne.nom_scenario_cible, "Sc_M3-5_c10")
        self.assertEqual(campagne.commentaire, "")

    def test_prepare_external_runs_from_otfa(self):
        if WRITE_REFERENCE_FILES:
            self.fichierotfa.prepare_external_runs_from_otfa(
                os.path.join('crue10', 'tests', 'data', 'ref', VERSION_GRAMMAIRE_COURANTE, 'otfa'),
                ['VS2017', 'gcc'],
                force=True,
            )
        self.fichierotfa.prepare_external_runs_from_otfa(
            os.path.join('crue10', 'tests', 'data', 'out', VERSION_GRAMMAIRE_COURANTE, 'otfa'),
            ['VS2017', 'gcc'],
        )
