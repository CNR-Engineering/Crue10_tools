# coding: utf-8
from collections import OrderedDict
from datetime import datetime
from glob import glob
from io import open
import os.path

from crue10.run.results import RunResults
from crue10.run.trace import Trace
from crue10.utils import add_default_missing_metadata, ExceptionCrue10, logger
from crue10.utils.crueconfigmetier import ENUM_SEVERITE
from crue10.utils.settings import GRAVITE_MIN, GRAVITE_MIN_ERROR


FMT_RUN_IDENTIFIER = "R%Y-%m-%d-%Hh%Mm%Ss"


def get_path_file_unique_matching(folder, ext_pattern):
    file_path_list= []
    for file_path in glob(os.path.join(folder, ext_pattern)):
        file_path_list.append(file_path)
    if len(file_path_list) == 0:
        raise ExceptionCrue10("Aucun fichier `%s` trouvé dans le dossier du %s" % ext_pattern)
    elif len(file_path_list) > 1:
        raise ExceptionCrue10("Plusieurs fichiers `%s` trouvés dans le dossier du %s" % ext_pattern)
    return file_path_list[0]


def get_run_identifier(datetime_obj=None):
    if datetime_obj is None:
        return datetime.now().strftime(FMT_RUN_IDENTIFIER)
    else:
        return datetime_obj.strftime(FMT_RUN_IDENTIFIER)


class Run:
    """
    Run
    - id: run identifier corresponding to folder name
    - run_mo_path <str>: path to the folder of the model (corresponds to the longest path)
    - metadata <dict>: containing metadata (keys correspond to `METADATA_FIELDS` list)
    - traces <OrderedDict>: list of traces for each service
    """

    SERVICES = ['r', 'g', 'i', 'c']
    SERVICES_NAMES = {
        'r': 'pré-traitements réseau',
        'g': 'pré-traitements géométriques',
        'i': 'pré-traitements conditions initiales',
        'c': 'calcul',
    }
    FILES_CSV = ['cptr', 'cptg', 'cpti', 'ccal']
    FILES_XML = ['rptr', 'rptg', 'rpti', 'rcal']
    METADATA_FIELDS = ['Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif', 'DateDerniereModif']

    def __init__(self, run_mo_path, metadata=None):
        self.id = os.path.basename(os.path.normpath(os.path.join(run_mo_path, '..')))
        self.run_mo_path = run_mo_path
        self.metadata = self.metadata = {} if metadata is None else metadata
        self.metadata = add_default_missing_metadata(self.metadata, Run.METADATA_FIELDS)
        self.traces = OrderedDict([(service, []) for service in Run.SERVICES])

    def read_traces(self):
        for service, csv_type in zip(Run.SERVICES, Run.FILES_CSV):
            csv_path = get_path_file_unique_matching(self.run_mo_path, '*.' + csv_type + '.csv')
            with open(csv_path, 'r') as in_csv:
                for row in in_csv:
                    self.traces[service].append(Trace(row.replace('\n', '')))

    def get_service_traces(self, service, gravite_min=GRAVITE_MIN):
        gravite_min_int = ENUM_SEVERITE[gravite_min]
        if service not in Run.SERVICES:
            raise ExceptionCrue10("Le service `%s` n'est pas reconnu" % service)
        return [str(trace) for trace in self.traces[service] if trace.gravite_int <= gravite_min_int]

    def nb_avertissements(self, services=SERVICES):
        nb = 0
        for service in services:
            nb += len(self.get_service_traces(service, gravite_min='WARN'))
        return nb

    def nb_erreurs(self, services=SERVICES):
        nb = 0
        for service in services:
            nb += len(self.get_service_traces(service, gravite_min=GRAVITE_MIN_ERROR))
        return nb

    def get_all_traces(self, services=SERVICES, gravite_min=GRAVITE_MIN):
        text = ''
        for service in services:
            text = '~> Traces du service "%s"\n' % Run.SERVICES_NAMES[service]
            text += '\n'.join(self.get_service_traces(service, gravite_min=gravite_min))
            text += '\n'
        return text

    def get_service_time(self, service):
        if service not in Run.SERVICES:
            raise ExceptionCrue10("Le service `%s` n'est pas reconnu" % service)
        for trace in self.traces[service]:
            if trace.id == 'ID_TIMING':
                return float(trace.parametres[0].replace('"', ''))

    def get_time(self, services=SERVICES):
        time = 0
        for service in services:
            time += self.get_service_time(service)
        return time

    def get_resultats_pretraitements_geometriques(self):
        raise NotImplementedError  # TODO

    def has_computation_traces(self):
        return len(self.traces['c']) != 0

    def get_results(self):
        # Check that some traces were read
        if not self.has_computation_traces:
            # Remark: rcal.xml should not exist in this case (a previous service encounters a problem)
            raise ExceptionCrue10("Le run #%s ne contient pas de traces (ou vous avez oubliez `read_traces`)"
                                  % self.id)

        # Check if errors are in computation traces
        traces_errors = self.get_service_traces(service='c', gravite_min=GRAVITE_MIN_ERROR)
        if traces_errors:
            logger.warn("Le run #%s contient des résultats partiels car les traces correspondent à "
                        "des erreurs de calculs :" % self.id)
            logger.warn('\n'.join(traces_errors))

        # Get file and returns results
        rcal_path = get_path_file_unique_matching(self.run_mo_path, '*.rcal.xml')
        return RunResults(rcal_path)

    def __repr__(self):
        text = "Run %s" % self.id
        if self.traces[Run.SERVICES[0]]:
            text += ' (%i avertissement(s) dont %i erreur(s) au total, ' % (self.nb_avertissements(), self.nb_erreurs())
            if not self.traces['c']:
                text += 'pas de calcul'
            else:
                text += '%i avertissement(s) dont %i erreur(s) de calculs'\
                        % (self.nb_avertissements(['c']), self.nb_erreurs(['c']))
            text += ')'
        return text
