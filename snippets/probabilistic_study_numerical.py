"""
Etude probabiliste sur les paramètres numériques de calculs pseudo-permanents

- pas de temps (constant)
- paramètres de convergence : TolMaxZ, TolMaxQ

Attention: le nom de la distribution doit correspondre au mot-clé de la modification à appliquer.

## Exemple de fin de listing
INFO: => Temps génération de tous les runs = 143.0s
INFO: BILAN DES CALCULS CRUE10
INFO: * Nombre de Run avec au moins une erreur bloquante = 379
INFO: * Temps total passé dans Crue10.exe = 298.9s (moyenne par run: 0.30s)
INFO:   Répartition par service : {'pré-traitements réseau': '13%', 'pré-traitements géométriques': '11%', 'pré-traitements conditions initiales': '1%', 'calcul': '72%'}
"""
import logging
from math import log
import numpy as np
import openturns as ot
import os.path
import pandas as pd
import seaborn as sns
from time import perf_counter

from crue10.etude import Etude
from crue10.run import Run
from crue10.utils import logger
from crue10.utils.multiple_runs import launch_scenario_modifications
from crue10.utils.settings import CSV_DELIMITER


NB_SAMPLES = 1000
IDX_CALC = -1  # index (0-indexed) du calcul pseudo-permanent à étudier (-1 = dernier calcul)

SAMPLE, RUN, POST = False, True, True

OUT_FOLDER = os.path.join('out', 'probabilistic_study_numerical')
CSV_SAMPLES = os.path.join(OUT_FOLDER, 'probabilistic_study_numerical_sample.csv')
RUN_PREFIX = 'SensiNum'


logger.setLevel(logging.INFO)

etude = Etude(os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc',
                               'Etu_SY2016_Conc', 'Etu_SY2016_Conc.etu.xml'))
etude.read_all()
nom_scenario = 'Sc_' + RUN_PREFIX
if RUN:
    etude.supprimer_scenario(nom_scenario, ignore=True, sleep=1.0)  # supprime le scénario s'il existe déjà
    scenario = etude.ajouter_scenario_par_copie('Sc_calage_permanent', nom_scenario)
else:
    scenario = etude.get_scenario(nom_scenario)

if SAMPLE:
    # Build all probability distributions
    distributions = []

    distrib = ot.LogUniform(log(1.0), log(3600.0 * 24))
    distrib.setName('pnum.CalcPseudoPerm.Pdt')
    distributions.append(distrib)

    distrib = ot.LogUniform(log(0.001), log(0.5))
    distrib.setName('pnum.CalcPseudoPerm.TolMaxZ')
    distributions.append(distrib)

    distrib = ot.LogUniform(log(0.001), log(10.0))
    distrib.setName('pnum.CalcPseudoPerm.TolMaxQ')
    distributions.append(distrib)

    # Build a ComposedDistribution (with independent copula) and sample it
    input_vector = ot.ComposedDistribution(distributions)
    sample = input_vector.getSample(NB_SAMPLES)

    # Build and write df_sample in a CSV file
    df_sample = pd.DataFrame(data=np.array(sample),
                             columns=[distrib.getName() for distrib in distributions],
                             index=[RUN_PREFIX + str(i).zfill(3) for i in range(NB_SAMPLES)])
    df_sample.to_csv(CSV_SAMPLES, sep=CSV_DELIMITER)


# Load df_sample from a CSV file and add a column for comments
df_sample = pd.read_csv(CSV_SAMPLES, index_col=0, header=0, delimiter=CSV_DELIMITER)
x_vars = list(df_sample.columns)
df_sample['comment'] = ['\n'.join([' * ' + key + ' = ' + str(value) for key, value in row.to_dict().items()])
                        for run_id, row in df_sample.iterrows()]

if RUN:
    # Build list of modifications (converts dataframe to a list of dictionaries)
    modifications_liste = []
    for run_id, serie in df_sample.iterrows():
        modifications = serie.to_dict()
        modifications['run_id'] = run_id
        modifications_liste.append(modifications)

    # Get the modification function
    def apply_modifications(modifications):
        return scenario.get_function_apply_modifications(etude)(modifications)


if __name__ == '__main__':
    if RUN:
        # Performs a parallel computation
        t1 = perf_counter()
        runs_liste = launch_scenario_modifications(apply_modifications, modifications_liste)
        t2 = perf_counter()
        logger.info("=> Temps génération de tous les runs = {:.1f}s".format(t2 - t1))  # 127s on laptop P52 (on C:\)

        # Write a clean etu.xml file
        for run in runs_liste:
            scenario.ajouter_run(run)
        scenario.set_run_courant(runs_liste[-1].id)
        etude.write_etu()
    elif POST:
        runs_liste = [scenario.get_run(run_id) for run_id in scenario.get_liste_noms_runs()]

    if POST:
        nom_sections = ['St_RET155.030',  # Fk_RET5min
                        'St_RET160.300',  # Fk_RET3min
                        'St_RET162.000']  # Fk_RET1min

        # Build a dataframe with input parameters
        df_all = df_sample
        del df_all['comment']  # Remove column

        # Add output parameters
        df_all['has_errors'] = True
        y_vars = ['computation_time']
        df_all['computation_time'] = np.nan
        for nom_section in nom_sections:
            colname = 'Z_' + nom_section
            y_vars.append(colname)
            df_all[colname] = np.nan

        # Fill df_all from Crue10 results
        crue_time = {service: 0.0 for service in Run.SERVICES}
        for run in runs_liste:
            # Compute time spent by each service (estimated by Crue10 core)
            for service in Run.SERVICES:
                time = run.get_service_time(service)
                crue_time[service] += time
                if service == 'c':
                    df_all.at[run.id, 'computation_time'] = time

            # Check that run does not contains errors
            if run.nb_erreurs_bloquantes() == 0:
                df_all.at[run.id, 'has_errors'] = False
                resultats = run.get_resultats_calcul()
                values = resultats.get_res_all_steady_var_at_emhs('Z', nom_sections)[IDX_CALC]
                for i, nom_section in enumerate(nom_sections):
                    df_all.at[run.id, 'Z_' + nom_section] = values[i]

        crue_time_tot = sum([time for service, time in crue_time.items()])
        crue_time_adm = {Run.SERVICES_NAMES[service]: str(int(100*time/crue_time_tot)) + '%'
                         for service, time in crue_time.items()}
        nb_errors = df_all['has_errors'].sum()

        logger.info("BILAN DES CALCULS CRUE10")
        logger.info("* Nombre de Run avec au moins une erreur bloquante = %i" % nb_errors)
        logger.info("* Temps total passé dans Crue10.exe = {:.1f}s "
                    "(moyenne par run: {:.2f}s)".format(crue_time_tot, crue_time_tot/NB_SAMPLES))
        logger.info("  Répartition par service : %s" % crue_time_adm)

        # Write a CSV file and generate some figures
        df_all.to_csv(os.path.join(OUT_FOLDER, 'probabilistic_study_numerical_all.csv'), sep=CSV_DELIMITER)

        sns_plot = sns.pairplot(df_all, vars=x_vars, hue='has_errors')
        sns_plot.set(xscale='log')
        sns_plot.savefig(os.path.join(OUT_FOLDER, 'probabilistic_study_numerical_matrix_X-X.png'))

        sns_plot = sns.pairplot(df_all[np.invert(df_all['has_errors'])], x_vars=x_vars, y_vars=y_vars)
        sns_plot.savefig(os.path.join(OUT_FOLDER, 'probabilistic_study_numerical_matrix_Y-X.png'))
