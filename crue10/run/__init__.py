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
from crue10.utils.settings import GRAVITE_AVERTISSEMENT, GRAVITE_MAX, GRAVITE_MIN, GRAVITE_MIN_ERROR


FMT_RUN_IDENTIFIER = "R%Y-%m-%d-%Hh%Mm%Ss"


def get_path_file_unique_matching(folder, ext_pattern):
    file_path_list= []
    for file_path in glob(os.path.join(folder, ext_pattern)):
        file_path_list.append(file_path)
    if len(file_path_list) == 0:
        raise IOError("Aucun fichier `%s` trouvé dans le dossier `%s`" % (ext_pattern, folder))
    elif len(file_path_list) > 1:
        raise ExceptionCrue10("Plusieurs fichiers `%s` trouvés dans le dossier `%s`" % (ext_pattern, folder))
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
    - run_path <str>: path to the folder of the run (exactly one folder before run_mo_path)
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
        self.run_path = os.path.normpath(os.path.join(run_mo_path, '..'))
        self.id = os.path.basename(self.run_path)
        self.run_mo_path = run_mo_path
        self.metadata = self.metadata = {} if metadata is None else metadata
        self.metadata = add_default_missing_metadata(self.metadata, Run.METADATA_FIELDS)
        self.traces = OrderedDict([(service, []) for service in Run.SERVICES])

    def read_traces(self):
        # Check stdout.csv (only compulsory output file)
        csv_path = os.path.join(self.run_path, 'stdout.csv')
        with open(csv_path, 'r') as in_csv:
            for row in in_csv:
                if 'chargement OK scenario' in row:
                    break  # Stop parsing stdout.csv because traces of first service should exist
                if not(row.startswith('Crue10_CoeurEtudes') or row.startswith('*****')) and row != '':
                    trace = Trace(row)
                    if trace.is_erreur():
                        raise ExceptionCrue10("Une erreur critique dans stdout.csv:\n%s" % trace)

        # Read traces of each 4 services
        for service, csv_type in zip(Run.SERVICES, Run.FILES_CSV):
            try:
                csv_path = get_path_file_unique_matching(self.run_mo_path, '*.' + csv_type + '.csv')
            except IOError as e:
                logger.warn("Le service `%s` n'a pas de trace :\n%s" % (Run.SERVICES_NAMES[service], e))
                return  # further services will not have a csv with traces
            with open(csv_path, 'r') as in_csv:
                for row in in_csv:
                    self.traces[service].append(Trace(row.replace('\n', '')))

    def get_service_traces(self, service, gravite_min=GRAVITE_MIN, gravite_max=GRAVITE_MAX):
        gravite_min_int = ENUM_SEVERITE[gravite_min]
        gravite_max_int = ENUM_SEVERITE[gravite_max]
        if service not in Run.SERVICES:
            raise ExceptionCrue10("Le service `%s` n'est pas reconnu" % service)
        return [str(trace) for trace in self.traces[service]
                if gravite_min_int >= trace.gravite_int >= gravite_max_int]

    def nb_avertissements(self, services=SERVICES):
        nb = 0
        for service in services:
            nb += len(self.get_service_traces(service, gravite_min=GRAVITE_AVERTISSEMENT,
                                              gravite_max=GRAVITE_AVERTISSEMENT))
        return nb

    def nb_avertissements_calcul(self):
        return self.nb_avertissements(['c'])

    def nb_erreurs(self, services=SERVICES):
        nb = 0
        for service in services:
            nb += len(self.get_service_traces(service, gravite_min=GRAVITE_MIN_ERROR))
        return nb

    def nb_erreurs_calcul(self):
        return self.nb_erreurs(['c'])

    def get_all_traces(self, services=SERVICES, gravite_min=GRAVITE_MIN, gravite_max=GRAVITE_MAX):
        text = ''
        for service in services:
            text = '~> Traces du service "%s"\n' % Run.SERVICES_NAMES[service]
            text += '\n'.join(self.get_service_traces(service, gravite_min=gravite_min, gravite_max=gravite_max))
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
            logger.warn("Le run #%s contient des résultats partiels car des erreurs "
                        "se trouvent dans les traces du calcul :\n%s" % (self.id, '\n'.join(traces_errors)))

        # Get file and returns results
        rcal_path = get_path_file_unique_matching(self.run_mo_path, '*.rcal.xml')
        return RunResults(rcal_path)

    def __repr__(self):
        text = "Run %s" % self.id
        if self.traces[Run.SERVICES[0]]:
            text += ' (%i avertissement(s) + %i erreur(s) au total, '\
                    % (self.nb_avertissements(), self.nb_erreurs())
            if not self.traces['c']:
                text += 'pas de calcul'
            else:
                text += '%i avertissement(s) + %i erreur(s) de calculs'\
                        % (self.nb_avertissements_calcul(), self.nb_erreurs_calcul())
            text += ')'
        return text
