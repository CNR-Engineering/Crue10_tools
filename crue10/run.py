# coding: utf-8
from datetime import datetime
from glob import glob
import os.path

from crue10.results import RunResults
from crue10.utils import add_default_missing_metadata, ExceptionCrue10


FMT_RUN_IDENTIFIER = "R%Y-%m-%d-%Hh%Mm%Ss"


def get_run_identifier(datetime_obj=None):
    if datetime_obj is None:
        return datetime.now().strftime(FMT_RUN_IDENTIFIER)
    else:
        return datetime_obj.strftime(FMT_RUN_IDENTIFIER)


class Run:
    """
    Run
    - id: run identifier corresponding to folder name
    - mo_folder <str>: path to run modele folder
    - metadata <{dict}>: containing metadata (keys correspond to `METADATA_FIELDS` list)
    """

    METADATA_FIELDS = ['Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif', 'DateDerniereModif']

    def __init__(self, run_mo_run, metadata=None):
        self.id = os.path.basename(os.path.normpath(os.path.join(run_mo_run, '..')))
        self.run_mo_path = run_mo_run
        self.metadata = self.metadata = {} if metadata is None else metadata
        self.metadata = add_default_missing_metadata(self.metadata, Run.METADATA_FIELDS)

    def get_results(self):
        # Find list of rcal files
        rcal_path_list = []
        if not os.path.exists(self.run_mo_path):
            raise ExceptionCrue10("Le dossier `%s` n'existe pas" % self.run_mo_path)
        for rcal_path in glob(os.path.join(self.run_mo_path, '*.rcal.xml')):
            rcal_path_list.append(rcal_path)

        # Check that only a single rcal file is found
        if len(rcal_path_list) == 0:
            raise ExceptionCrue10("Aucun fichier rcal trouvé dans le dossier du %s" % self)
        elif len(rcal_path_list) > 1:
            raise ExceptionCrue10("Plusieurs fichiers rcal trouvés dans le dossier du %s" % self)

        return RunResults(rcal_path_list[0])

    def __repr__(self):
        return "Run %s" % self.id
