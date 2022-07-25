from glob import glob
import os.path

from crue10.base import EnsembleFichiersXML
from crue10.etude import Etude
from crue10.utils import check_isinstance

from snippets._params import ETATREF_SCENARIO_PAR_AMENAGEMENT


DOSSIER = os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc')


class Campagne:
    """
    Campagne OTFA
    """

    def __init__(self, chemin_etude, nom_scenario):
        self.chemin_etude = chemin_etude
        self.nom_scenario = nom_scenario


class FichierOtfa(EnsembleFichiersXML):
    """
    Fichier OTFA
    """

    FILES_XML = ['otfa']
    METADATA_FIELDS = ['Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, nom_campagne, access='r', files=None, metadata=None):
        self.id = nom_campagne
        super().__init__(access, files, metadata)
        self.campagnes = []

    def ajouter_campagne(self, campagne):
        check_isinstance(campagne, Campagne)
        self.campagnes.append(campagne)

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


otfa = FichierOtfa('Conc', access='w', files={'otfa': 'Conc.otfa.xml'},
                   metadata={'Commentaire': "OTFA pour les derniers modèles de concession"})

for etude_dossier, nom_scenario in ETATREF_SCENARIO_PAR_AMENAGEMENT.items():
    for etu_path in glob(os.path.join(DOSSIER, etude_dossier, '*.etu.xml')):  # FIXME: only one etu.xml should be found by folder!
        etude = Etude(etu_path)
        if nom_scenario is None:
            nom_scenario = etude.get_scenario_courant().id
        campagne = Campagne(os.path.relpath(etu_path, start=os.path.join(DOSSIER, 'OTFA_C10C10')), nom_scenario)
        otfa.ajouter_campagne(campagne)

otfa.write_otfa(os.path.join(DOSSIER, 'OTFA_C10C10'))
