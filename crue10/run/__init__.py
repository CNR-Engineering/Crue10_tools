# coding: utf-8
from collections import OrderedDict
from datetime import datetime
from glob import glob
from io import open
import os.path
import subprocess

from crue10.run.results import RunResults
from crue10.utils.settings import CRUE10_EXE_PATH, CRUE10_EXE_OPTS
from crue10.run.trace import Trace
from crue10.utils import add_default_missing_metadata, ExceptionCrue10, logger
from crue10.utils.crueconfigmetier import ENUM_SEVERITE
from crue10.utils.settings import GRAVITE_AVERTISSEMENT, GRAVITE_MAX, GRAVITE_MIN, \
    GRAVITE_MIN_ERROR, GRAVITE_MIN_ERROR_BLK


FMT_RUN_IDENTIFIER = "R%Y-%m-%d-%Hh%Mm%Ss"


def get_path_file_unique_matching(folder, ext_pattern):
    file_path_list = []
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

    :param id: run identifier corresponding to folder name
    :type id: str
    :param run_path: path to the folder of the run (exactly one folder before run_mo_path)
    :type run_path: str
    :param run_mo_path: path to the folder of the model (corresponds to the longest path)
    :type run_mo_path: str
    :param metadata: containing metadata (keys correspond to `METADATA_FIELDS` list)
    :type metadata: dict
    :param traces: list of traces for each service
    :type traces: OrderedDict
    """

    SERVICES = ['r', 'g', 'i', 'c']
    SERVICES_NAMES = {
        'r': 'pré-traitements réseau',
        'g': 'pré-traitements géométriques',
        'i': 'pré-traitements conditions initiales',
        'c': 'calcul',
    }
    FILES_CSV = {
        'r': 'cptr',
        'g': 'cptg',
        'i': 'cpti',
        'c': 'ccal',
    }
    FILES_XML = ['rptr', 'rptg', 'rpti', 'rcal']
    METADATA_FIELDS = ['Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif', 'DateDerniereModif']

    def __init__(self, etude_basename, run_mo_path, metadata=None):
        self.etude_basename = etude_basename
        self.run_path = os.path.normpath(os.path.join(run_mo_path, '..'))
        self.id = os.path.basename(self.run_path)
        self.run_mo_path = run_mo_path
        self.metadata = self.metadata = {} if metadata is None else metadata
        self.metadata = add_default_missing_metadata(self.metadata, Run.METADATA_FIELDS)
        self.traces = OrderedDict([(service, []) for service in Run.SERVICES])

    def _check_service(self, service):
        if service not in Run.SERVICES:
            raise ExceptionCrue10("Le service `%s` est inconnu" % service)

    def _check_services(self, services):
        for service in services:
            self._check_service(service)

    def launch_services(self, services, exe_path=CRUE10_EXE_PATH):
        """
        Exécuter un Run avec plusieurs services

        Attention:
            - aucune vérification de la pertinence des services (en fonction de ceux déjà lancés)
            - les fichiers de sortie de crue10.exe sont écrasés s'ils existent déjà

        :param services: liste des services
        :type services: list(str)
        :param exe_path: chemin vers l'exécutable crue10.exe
        :type exe_path: str
        :return: run lancé
        :rtype: Run
        """
        self._check_services(services)

        exe_opts = ['-' + service for service in services]
        if not os.path.exists(exe_path) and exe_path.endswith('.exe'):
            raise ExceptionCrue10("Le chemin vers l'exécutable n'existe pas : `%s`" % exe_path)

        run_folder = self.run_path

        # Run crue10.exe in command line and redirect stdout and stderr in csv files
        etu_path = os.path.join(run_folder, self.etude_basename)
        cmd_list = [exe_path] + exe_opts + [etu_path]
        logger.info("Éxécution : %s" % ' '.join(cmd_list))
        with open(os.path.join(run_folder, 'stdout.csv'), "w") as out_csv:
            with open(os.path.join(run_folder, 'stderr.csv'), "w") as err_csv:
                exit_code = subprocess.call(cmd_list, stdout=out_csv, stderr=err_csv)
                # exit_code is always to 0 even in case of computation error...

        self.read_traces(services)

    def read_traces(self, services=SERVICES):
        self._check_services(services)

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

        # Read traces of each services
        for service in services:
            csv_type = Run.FILES_CSV[service]
            try:
                csv_path = get_path_file_unique_matching(self.run_mo_path, '*.' + csv_type + '.csv')
            except IOError as e:
                logger.warn("Le service `%s` n'a pas de trace :\n%s" % (Run.SERVICES_NAMES[service], e))
                return  # further services will not have a csv with traces
            with open(csv_path, 'r') as in_csv:
                for row in in_csv:
                    self.traces[service].append(Trace(row.replace('\n', '')))

    def get_service_traces(self, service, gravite_min=GRAVITE_MIN, gravite_max=GRAVITE_MAX):
        self._check_service(service)
        gravite_min_int = ENUM_SEVERITE[gravite_min]
        gravite_max_int = ENUM_SEVERITE[gravite_max]
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

    def nb_erreurs_bloquantes(self, services=SERVICES):
        nb = 0
        for service in services:
            nb += len(self.get_service_traces(service, gravite_min=GRAVITE_MIN_ERROR_BLK))
        return nb

    def get_all_traces(self, services=SERVICES, gravite_min=GRAVITE_MIN, gravite_max=GRAVITE_MAX):
        self._check_services(services)
        text = ''
        for service in services:
            text += '~> Traces du service "%s"\n' % Run.SERVICES_NAMES[service]
            text += '\n'.join(self.get_service_traces(service, gravite_min=gravite_min, gravite_max=gravite_max))
            text += '\n'
        return text

    def get_all_traces_above_warn(self, services=SERVICES, gravite_max=GRAVITE_MAX):
        return self.get_all_traces(services, gravite_min=GRAVITE_AVERTISSEMENT, gravite_max=gravite_max)

    def get_service_time(self, service):
        self._check_service(service)
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
            # Remark: rcal.xml should not exist in this case (a previous service encountered a problem)
            raise ExceptionCrue10("Le run #%s ne contient pas de traces (ou vous avez oublié `read_traces`)"
                                  % self.id)

        # Check if errors are in computation traces
        traces_errors = self.get_service_traces(service='c', gravite_min=GRAVITE_MIN_ERROR_BLK)
        if traces_errors:
            logger.warn("Le run #%s contient des résultats partiels car des erreurs bloquantes "
                        "se trouvent dans les traces du calcul :\n%s" % (self.id, '\n'.join(traces_errors)))

        # Get file and returns results
        rcal_path = get_path_file_unique_matching(self.run_mo_path, '*.rcal.xml')
        return RunResults(rcal_path)

    def set_comment(self, comment):
        self.metadata['Commentaire'] = comment

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
