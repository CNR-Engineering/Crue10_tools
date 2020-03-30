"""
Probabilistic study example
"""
import logging
import numpy as np
import openturns as ot
import os.path
import pandas as pd
import seaborn as sns
from time import perf_counter

from crue10.etude import Etude
from crue10.utils import logger
from crue10.utils.multiple_runs import launch_scenario_modifications
from crue10.utils.settings import CSV_DELIMITER


NB_SAMPLES = 1000
LOIS_FROTTEMENT = ['Fk_RET1min', 'Fk_RET2min', 'Fk_RET3min', 'Fk_RET4min', 'Fk_RET5min', 'Fk_RET6min']
DELTA_SIGMA_STRICKLER = 5.0  # m^(1/3)/s
ND_QAPP_AMONT = ['Nd_RET162.000']
DELTA_REL_QAPP = 0.1  # 10%
IDX_CALC = -1  # index du calcul pseudo-permanent à étudier

SAMPLE, RUN, POST = False, True, True

CSV_SAMPLES = os.path.join('out', 'probabilistic_study_sample.csv')


logger.setLevel(logging.INFO)

etude = Etude(os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc',
                               'Etu_SY2016_Conc', 'Etu_SY2016_Conc.etu.xml'))
etude.read_all()
scenario = etude.get_scenario('Sc_calage_permanent')


if SAMPLE:
    # Build all distributions
    distributions = []
    for nom_loi in LOIS_FROTTEMENT:
        value = scenario.modele.get_loi_frottement(nom_loi).get_loi_Fk_value()
        distrib = ot.TruncatedNormal(value, DELTA_SIGMA_STRICKLER, 5.0, 80.0)
        distributions.append(distrib)
    distrib = ot.Uniform(1.0 - DELTA_REL_QAPP, 1.0 + DELTA_REL_QAPP)
    distributions.append(distrib)

    # Build a ComposedDistribution and sample it
    input_vector = ot.ComposedDistribution(distributions)
    sample = input_vector.getSample(NB_SAMPLES)

    # Build and write df_sample in a CSV file
    df_sample = pd.DataFrame(data=np.array(sample),
                             columns=LOIS_FROTTEMENT + ['Qapp_factor.' + ND_QAPP_AMONT[0]],
                             index=['Run' + str(i).zfill(3) for i in range(NB_SAMPLES)])
    df_sample.to_csv(CSV_SAMPLES, sep=CSV_DELIMITER)

else:
    # Load df_sample from a CSV file
    df_sample = pd.read_csv(CSV_SAMPLES, index_col=0, delimiter=CSV_DELIMITER)


if RUN:
    scenario.remove_all_runs(sleep=1.0)

    # Build list of modifications
    modifications_liste = []
    for run_id, serie in df_sample.iterrows():
        modifications = serie.to_dict()
        modifications['run_id'] = run_id
        modifications_liste.append(modifications)

    # Get the modification function
    def apply_modifications(modifications):
        return scenario.get_function_apply_modifications(etude)(modifications)


if __name__ == '__main__':
    x_vars = list(df_sample.columns)

    if RUN:
        # Performs a parallel computation
        t1 = perf_counter()
        runs_liste = launch_scenario_modifications(apply_modifications, modifications_liste)
        t2 = perf_counter()
        logger.info("=> Temps génération de tous les runs = {}s".format(t2 - t1))  # 127s on laptop P52 (on C:\)

        # Write a clean etu.xml file
        for run in runs_liste:
            scenario.add_run(run)
        scenario.set_current_run_id(runs_liste[-1].id)
        etude.write_etu()
    else:
        runs_liste = [scenario.get_run(run_id) for run_id in scenario.get_liste_run_ids()]

    if POST:

        df_all = df_sample
        df_all['has_errors'] = False
        nom_sections = ['St_RET155.030',  # Fk_RET5min
                        'St_RET160.300',  # Fk_RET3min
                        'St_RET162.000']  # Fk_RET1min
        y_vars = []
        for nom_section in nom_sections:
            colname = 'Z_' + nom_section
            y_vars.append(colname)
            df_all[colname] = np.nan

        crue_time = 0
        for run in runs_liste:
            crue_time += run.get_time()
            if run.nb_erreurs() > 0:
                df_sample[run.id] = True
            results = run.get_results()
            values = results.get_res_all_steady_var_at_emhs('Z', nom_sections)[IDX_CALC]
            for i, nom_section in enumerate(nom_sections):
                df_all.at[run.id, 'Z_' + nom_section] = values[i]

        nb_errors = df_all['has_errors'].sum()
        logger.info("=> Nombre d'échec = {}".format(nb_errors))
        logger.info("=> Temps total passé dans Crue10.exe = {:.1f}s "
                    "(moyenne par run: {:.2f}s)".format(crue_time, crue_time/NB_SAMPLES))

        df_all.to_csv(os.path.join('out', 'probabilistic_study_all.csv'), sep=CSV_DELIMITER)

        sns_plot = sns.pairplot(df_all, vars=x_vars, hue='has_errors')
        sns_plot.savefig(os.path.join('out', 'probabilistic_study_matrix_X-X.png'))

        sns_plot = sns.pairplot(df_all[df_all['has_errors'] == 0], x_vars=x_vars, y_vars=y_vars)
        sns_plot.savefig(os.path.join('out', 'probabilistic_study_matrix_Y-X.png'))
