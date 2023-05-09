# coding: utf-8
from glob import glob
import os

from crue10.base import EnsembleFichiersXML
from crue10.etude import Etude
from crue10.utils import check_isinstance, get_optional_commentaire, PREFIX

from snippets._params import ETATREF_SCENARIO_PAR_AMENAGEMENT


DOSSIER_REF = os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc')
DOSSIER_CIBLE = os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc_g1.3')


class Campagne:
    """
    Campagne OTFA
    """

    def __init__(self, chemin_etude_ref, nom_scenario_ref, chemin_etude_cible='', nom_scenario_cible='', commentaire=''):
        self.chemin_etude_ref = chemin_etude_ref
        self.nom_scenario_ref = nom_scenario_ref
        self.chemin_etude_cible = chemin_etude_cible
        self.nom_scenario_cible = nom_scenario_cible
        self.commentaire = commentaire


class FichierOtfa(EnsembleFichiersXML):
    """
    Fichier OTFA
    """

    FILES_XML = ['otfa']
    METADATA_FIELDS = ['Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, nom_campagne, mode='r', files=None, metadata=None):
        self.id = nom_campagne
        super().__init__(mode, files, metadata)
        self.campagnes = []

    def ajouter_campagne(self, campagne):
        check_isinstance(campagne, Campagne)
        self.campagnes.append(campagne)

    def read_otfa(self):
        root = self._get_xml_root_set_version_grammaire_and_comment('otfa')

        lignescampagnes_elt = root.find(PREFIX + 'LignesCampagne')
        for lignecampagnes_elt in lignescampagnes_elt.findall(PREFIX + 'LigneCampagne'):
            # Commentaire
            commentaire = get_optional_commentaire(lignecampagnes_elt)

            # Reference
            reference_elt = lignecampagnes_elt.find(PREFIX + 'Reference')
            chemin_etude_ref = reference_elt.find(PREFIX + 'Etude').text
            nom_scenario_ref = reference_elt.find(PREFIX + 'Scenario').text

            # Cible
            cible_elt = lignecampagnes_elt.find(PREFIX + 'Cible')
            etude_cible_elt = cible_elt.find(PREFIX + 'Etude')
            chemin_etude_cible = ''
            if etude_cible_elt is not None:
                chemin_etude_cible = etude_cible_elt.text
                if chemin_etude_cible is None:
                    chemin_etude_cible = ''
            nom_scenario_cible = cible_elt.find(PREFIX + 'Scenario').text
            if nom_scenario_cible is None:
                nom_scenario_cible = ''

            campagne = Campagne(chemin_etude_ref, nom_scenario_ref,
                                chemin_etude_cible, nom_scenario_cible, commentaire)
            self.ajouter_campagne(campagne)

    def ajouter_cible(self, folder):
        for campagne in self.campagnes:
            # assert campagne.chemin_etude_cible == ''
            # assert campagne.nom_scenario_cible == ''
            folder_end = campagne.chemin_etude_ref.replace('/', os.sep).split(os.sep)[-2:]
            campagne.chemin_etude_cible = os.path.join(folder, os.sep.join(folder_end))
            campagne.nom_scenario_cible = campagne.nom_scenario_ref

    def write_otfa(self, folder):
        """
        Ecrire le fichier otfa.xml

        :param folder: dossier de sortie
        """
        self._write_xml_file(
            'otfa', folder,
            metadata=self.metadata,
            campagnes=self.campagnes,
        )


# Complet.otfa.xml
otfa = FichierOtfa('Complet', mode='w', files={'otfa': '../../Crue10_examples/Cas-tests/OTFA_C10C10/Complet.otfa.xml'},
                   metadata={'Commentaire': "Campagne complète : lancement de toutes les lignes OTFA pour les cas-tests fonctionnels"})
otfa.read_otfa()
otfa.ajouter_cible(os.path.join('..', '..', 'Cas-tests_g1.3'))
otfa.write_otfa('../../Crue10_examples/Cas-tests/OTFA_C10C10_NEW')


# Conc.otfa.xml
otfa = FichierOtfa('Conc', mode='w', files={'otfa': 'Conc.otfa.xml'},
                   metadata={'Commentaire': "OTFA pour les derniers modèles de concession"})
for etude_dossier, nom_scenario in ETATREF_SCENARIO_PAR_AMENAGEMENT.items():
    for etu_path in glob(os.path.join(DOSSIER_REF, etude_dossier, '*.etu.xml')):  # FIXME: only one etu.xml should be found by folder!
        etude = Etude(etu_path)
        if nom_scenario is None:
            nom_scenario = etude.get_scenario_courant().id
        campagne = Campagne(os.path.relpath(etu_path, start=os.path.join(DOSSIER_REF, 'OTFA_C10C10')), nom_scenario,
                            os.path.relpath(os.path.join(DOSSIER_CIBLE, etude_dossier, os.path.basename(etu_path)),
                                            start=os.path.join(DOSSIER_REF, 'OTFA_C10C10')), nom_scenario)
        otfa.ajouter_campagne(campagne)

otfa.write_otfa(os.path.join(DOSSIER_REF, 'OTFA_C10C10'))
