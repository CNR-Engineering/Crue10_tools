# coding: utf-8
from filecmp import dircmp
import os.path
import unittest

from crue10.etude import Etude
from crue10.tests import DATA_TESTS_FOLDER_ABSPATH
from crue10.utils.settings import VERSION_GRAMMAIRE_COURANTE, VERSION_GRAMMAIRE_PRECEDENTE


NB_XML_FILES = 4 + 6 + 5 + 1

DEFAULT_METADATA = {
    'AuteurCreation': 'USERNAME',
    'DateCreation': '2000-01-01T00:00:00.000',
    'AuteurDerniereModif': 'USERNAME',
    'DateDerniereModif': '2000-01-01T00:00:00.000',
}


class EndToEndTestCase(unittest.TestCase):

    def _same_folders(self, folder_in, folder_out, version_grammaire, etu_changed=True):
        comparison = dircmp(folder_in, folder_out, ignore=['Config', 'CONFIG'])

        nb_common_xml = NB_XML_FILES
        if version_grammaire == VERSION_GRAMMAIRE_PRECEDENTE:
            nb_common_xml -= 1  # dreg

        has_error = False
        if len(comparison.common) != nb_common_xml:
            print("DIFF_FILES = %s" % comparison.diff_files)
            print("COMMON = %s" % comparison.common)
            has_error = True
        if len(comparison.left_only) != 0:
            print("LEFT ONLY = %s" % comparison.left_only)
            has_error = True
        if len(comparison.right_only) != 0:
            print("LEFT ONLY = %s" % comparison.right_only)
            has_error = True
        nb_diff_files = 1 if etu_changed else 0  # etu.xml
        if len(comparison.diff_files) != nb_diff_files:
            print("DIFF FILES = %s" % comparison.diff_files)
            has_error = True
        self.assertFalse(has_error)

    def _test_write_from_scratch(self, version_grammaire):
        folder_out = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'out', version_grammaire, 'Etu_from_scratch')
        etu_path = os.path.join(folder_out, 'Etu_from_scratch.etu.xml')
        etude = Etude(etu_path, mode='w', metadata=DEFAULT_METADATA, version_grammaire=version_grammaire)
        etude.create_empty_scenario('Sc_from_scratch', 'Mo_from_scratch', 'Sm_from_scratch',
                                    metadata=DEFAULT_METADATA)
        from snippets.construire_et_ecrire_sous_modele import sous_modele
        sous_modele.changer_version_grammaire(version_grammaire)
        sous_modele_out = etude.get_sous_modele('Sm_from_scratch')
        sous_modele_out.ajouter_emh_depuis_sous_modele(sous_modele)
        etude.write_all(ignore_shp=True)

        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', version_grammaire, 'Etu_from_scratch')
        self._same_folders(folder_in, folder_out, version_grammaire, etu_changed=False)

    def test_write_gcour_from_scratch(self):
        self._test_write_from_scratch(VERSION_GRAMMAIRE_COURANTE)

    def test_write_gprec_from_scratch(self):
        self._test_write_from_scratch(VERSION_GRAMMAIRE_PRECEDENTE)

    def test_read_gprec_and_write_all_gprec(self):
        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_PRECEDENTE, 'Etu3-6')
        etu_path = os.path.join(folder_in, 'Etu3-6.etu.xml')
        etude = Etude(etu_path)
        etude.read_all()
        folder_out = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'out', VERSION_GRAMMAIRE_PRECEDENTE, 'Etu3-6')
        etude.write_all(folder_out)
        self._same_folders(folder_in, folder_out, VERSION_GRAMMAIRE_PRECEDENTE, etu_changed=False)

    def test_read_gcour_and_write_all_gcour(self):
        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_COURANTE, 'Etu3-6')
        etu_path = os.path.join(folder_in, 'Etu3-6.etu.xml')
        etude = Etude(etu_path)
        etude.read_all()
        folder_out = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'out', VERSION_GRAMMAIRE_COURANTE, 'Etu3-6')
        etude.write_all(folder_out)
        self._same_folders(folder_in, folder_out, VERSION_GRAMMAIRE_COURANTE, etu_changed=False)

    def test_read_gprec_and_write_all_gcour(self):
        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_PRECEDENTE, 'Etu3-6')
        etu_path = os.path.join(folder_in, 'Etu3-6.etu.xml')
        etude = Etude(etu_path)
        etude.read_all()
        etude.changer_version_grammaire(VERSION_GRAMMAIRE_COURANTE)
        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_COURANTE, 'Etu3-6')
        folder_out = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'out', VERSION_GRAMMAIRE_COURANTE, 'Etu3-6')
        etude.write_all(folder_out)
        self._same_folders(folder_in, folder_out, VERSION_GRAMMAIRE_COURANTE, etu_changed=False)

    def test_read_gcour_and_write_all_gprec(self):
        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_COURANTE, 'Etu3-6')
        etu_path = os.path.join(folder_in, 'Etu3-6.etu.xml')
        etude = Etude(etu_path)
        etude.read_all()
        etude.changer_version_grammaire(VERSION_GRAMMAIRE_PRECEDENTE)
        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_PRECEDENTE, 'Etu3-6')
        folder_out = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'out', VERSION_GRAMMAIRE_PRECEDENTE, 'Etu3-6')
        etude.write_all(folder_out)
        self._same_folders(folder_in, folder_out, VERSION_GRAMMAIRE_PRECEDENTE, etu_changed=False)

    def test_read_gprec_and_write_all_gcour_grammaire(self):
        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_PRECEDENTE, 'Etu3-6_grammaire')
        etu_path = os.path.join(folder_in, 'Etu3-6.etu.xml')
        etude = Etude(etu_path)
        etude.read_all()
        etude.changer_version_grammaire(VERSION_GRAMMAIRE_COURANTE)
        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_COURANTE, 'Etu3-6_grammaire')
        folder_out = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'out', VERSION_GRAMMAIRE_COURANTE, 'Etu3-6_grammaire')
        etude.write_all(folder_out)
        self._same_folders(folder_in, folder_out, VERSION_GRAMMAIRE_COURANTE, etu_changed=False)

    def test_read_gcour_and_write_all_gprec_grammaire(self):
        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_COURANTE, 'Etu3-6_grammaire')
        etu_path = os.path.join(folder_in, 'Etu3-6.etu.xml')
        etude = Etude(etu_path)
        etude.read_all()
        etude.changer_version_grammaire(VERSION_GRAMMAIRE_PRECEDENTE)
        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_PRECEDENTE, 'Etu3-6_grammaire')
        folder_out = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'out', VERSION_GRAMMAIRE_PRECEDENTE, 'Etu3-6_grammaire')
        etude.write_all(folder_out)
        self._same_folders(folder_in, folder_out, VERSION_GRAMMAIRE_PRECEDENTE, etu_changed=False)
