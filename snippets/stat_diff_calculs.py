# coding: utf-8
"""
Statistiques calculées sur plusieurs variables lues aux sections du scénario courant
"""
from collections import OrderedDict
from glob import glob
import logging
import os
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
import seaborn as sns

from crue10.etude import Etude
from crue10.utils import logger


logger.setLevel(logging.ERROR)


RUN_CALCULATIONS, WRITE_DATAFRAMES, PLOT_BARPLOTS, PLOT_BOXPLOTS = False, False, True, True

SCENARIO_PAR_AMENAGEMENT = OrderedDict([
    # Scénario à utiliser par aménagement s'il diffère du "scénario courant" (dans ce cas, laisser `None`)
    # DTHR
    ('GE', 'Sc_Calperm_GE_QRef_br14'),
    ('SY', 'Sc_etats_ref'),
    ('CE', None),
    ('BY', 'Sc_BY2010_conc'),
    ('BC', None),
    ('SB', None),

    # DTRI
    ('PB', None),
    ('VS', None),
    ('PR', None),
    ('SV', None),

    # DTRS
    ('BV', None),
    ('BE', None),
    ('LN', None),
    ('MO', None),

    # DTRM
    ('DM', None),
    ('CA', 'Sc_CA2013_conc'),
    ('AV', None),
    ('VA', None),
    ('PA', None),
])

CRUE10_EXE = OrderedDict([
    # Référence utilisée pour les calculs de différences
    ('prod', 'P:/FudaaCrue/etc/coeurs/c10m10/exe/crue10.exe'.replace('/', os.sep)),

    # Calculs à comparer à la référence
    ('qualif', 'Q:/Qualif_Exec/FudaaCrue/etc/coeurs/c10m10/exe/crue10.exe'.replace('/', os.sep)),
    ('local', 'C:/PROJETS/SHY_C10_Crue10/BRANCHES/v10.3 (VS2017)/etc/coeurs/c10m10/exe/crue10.exe'.replace('/', os.sep)),
])

REFERENCE = CRUE10_EXE.keys()[0]

VARIABLE = 'Z'

OUT_CSV_STAT_FILE = 'out/stat_diff_calculs.csv'

OUT_CSV_DIFF_FILE = 'out/%s_diff_qualif-prod.csv'  # %s = amenagement

VARIABLE_LABELS = {
    'nb_calc_perm': u"Nb de calculs réussis",
    'nb_erreurs': u"Nb d'erreurs",
    'nb_avertissements': u"Nb d'avertissements",
}

# Calculs Crue10 et déduction des critères
if RUN_CALCULATIONS or WRITE_DATAFRAMES:
    df_stats = pd.DataFrame({'amenagement': [], 'exe':  [], 'variable': [], 'value': []})
    for folder in glob(os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc', '*')):
        amenagement = os.path.basename(folder)[4:6]

        for etu_path in glob(os.path.join(folder, '*.etu.xml')):
            etude = Etude(etu_path)
            etude.read_all()

            if SCENARIO_PAR_AMENAGEMENT[amenagement] is not None:
                etude.nom_scenario_courant = SCENARIO_PAR_AMENAGEMENT[amenagement]
            scenario = etude.get_scenario_courant()

            logger.error("%s: %i calculs" % (etu_path, scenario.get_nb_calc_pseudoperm))

            if RUN_CALCULATIONS:
                for exe, crue10_exe in CRUE10_EXE.items():
                    run = scenario.create_and_launch_new_run(etude, run_id=exe, exe_path=crue10_exe, force=True)
                    etude.write_etu()
                    logger.error(run)

            if WRITE_DATAFRAMES:
                res_perm = {}
                for exe in CRUE10_EXE.keys():
                    run = scenario.get_run(exe)
                    logger.debug("%s: %s" % (exe, run.traces['c'][0].get_message()))  # Check Crue10 version
                    results = run.get_results()

                    nb_calc_perm = len(results.calc_steady_dict)
                    values = {
                        'nb_calc_perm': nb_calc_perm,
                        'nb_erreurs': run.nb_erreurs_calcul(),
                        'nb_avertissements': run.nb_avertissements_calcul(),
                    }
                    for var, value in values.items():
                        df_append = pd.Series({
                            'amenagement': amenagement, 'exe': exe, 'variable': var, 'value': value,
                        })
                        df_stats = df_stats.append(df_append, ignore_index=True)

                    res_perm[exe] = results.get_res_all_steady_var_at_emhs('Z', results.emh['Section'])

                    # Calcul des différences
                    diff = res_perm[exe] - res_perm[REFERENCE][:nb_calc_perm, :]
                    diff_abs = np.abs(diff)

                    if exe == 'qualif':
                        df_diff = pd.DataFrame({
                            'id_calcul': np.repeat(np.arange(nb_calc_perm, dtype=np.int) + 1, diff.shape[1]),
                            'diff': diff.flatten()
                        })
                        df_diff.to_csv(OUT_CSV_DIFF_FILE % amenagement, sep=';', index=False)

                    # Calcul des critères
                    values = {
                        'MSD': np.mean(diff),
                        'MAD': np.mean(diff_abs),
                        'DIFF_ABS_MAX': diff_abs.max(),
                        'RMSD': np.sqrt(np.mean(diff**2)),
                    }
                    for var, value in values.items():
                        df_append = pd.Series({
                            'amenagement': amenagement, 'exe': exe, 'variable': var, 'value': value
                        })
                        df_stats = df_stats.append(df_append, ignore_index=True)

        if WRITE_DATAFRAMES:
            df_stats.to_csv(OUT_CSV_STAT_FILE, sep=';', index=False)


# Graphique avec les critères
if PLOT_BARPLOTS:
    # Read data to plot
    df_stats = pd.read_csv(OUT_CSV_STAT_FILE, delimiter=';')

    # Filter data
    df_stats = df_stats.loc[df_stats['exe'] != 'local', :]
    df_stats = df_stats.loc[df_stats['variable'] != 'nb_errors', :]
    # df_stats = df_stats.loc[(df_stats['amenagement'] != 'CA') & (df_stats['amenagement'] != 'AV'), :]

    # Build a FacetGrid object with barplots
    sns.set_context("notebook", font_scale=1.5, rc={"lines.linewidth": 2.5})
    g = sns.FacetGrid(df_stats, row="variable", sharex=True, sharey=False, size=3, aspect=4)
    g = g.map(sns.barplot, "amenagement", "value", "exe",
              order=SCENARIO_PAR_AMENAGEMENT.keys(), palette="husl", ci=None)

    # Sets ylabels from titles
    for i, ax in enumerate(g.axes[:, 0]):
        text = str(ax.get_title()).split(' = ')[1]
        if text in VARIABLE_LABELS:
            text = VARIABLE_LABELS[text]
        ax.set_ylabel(text)
        if i == 0:
            ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.22),
                      ncol=len(CRUE10_EXE), fancybox=True, shadow=True)
    g.set_titles("")

    g.set_xlabels(u"Aménagement (amont vers aval)")

    g.savefig(OUT_CSV_STAT_FILE.replace('.csv', '.png'))
    plt.close()


# Grapiques avec les boîtes à moustaches
if PLOT_BOXPLOTS:
    for amenagement in SCENARIO_PAR_AMENAGEMENT.keys():
        csv_path = OUT_CSV_DIFF_FILE % amenagement
        df_diff = pd.read_csv(csv_path, delimiter=';')

        g = sns.boxplot(x='id_calcul', y='diff', data=df_diff)
        g.set_xlabel(u"Numéro du calcul pseudo-permanent")
        g.set_ylabel(u"Différence qualif-prod")

        fig = g.get_figure()
        fig.set_size_inches(16.0, 6.0)
        fig.savefig(csv_path.replace('.csv', '.png'))
        plt.close()
