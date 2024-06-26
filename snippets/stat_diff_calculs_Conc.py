# coding: utf-8
"""
Statistiques sur les résultats des modèles Conc (scénario des états de référence)

Beware: compatibility with Python 2 is not tested for figures (at least you have to replace `height` argument by `size`)
"""
import logging
import os
import pandas as pd
from matplotlib import pyplot as plt
import seaborn as sns
from time import time

from crue10.campagne_otfa import FichierOtfa
from crue10.utils import logger
from crue10.utils.multiple_runs import get_run_steady_results, parse_otfa_runs
from _params import CRUE10_EXE, COEUR_REFERENCE, CSV_DELIMITER, \
    ETATREF_SCENARIO_PAR_AMENAGEMENT, write_csv


DOSSIER = "C:/PROJETS/Cas-tests_v10.5.0.0-VS2022/"
PARSE_OTFA, WRITE_DIFF_DATAFRAME, PLOT_RUN_BARPLOT, PLOT_DIFF_BARPLOT, PLOT_BOXPLOT = \
    True, True, True, True, True
REFERENCE = list(CRUE10_EXE.keys())[0]

# Nommage des fichiers de sortie du script
DOSSIER_OUT = os.path.join('..', 'tmp', 'stat_calculs_Conc')
os.makedirs(DOSSIER_OUT, exist_ok=True)
OUT_CSV_RUNS_FILE = os.path.join(DOSSIER_OUT, 'bilan_runs.csv')
OUT_CSV_DIFF_FILE = os.path.join(DOSSIER_OUT, 'bilan_stat_diff.csv')
OUT_CSV_DIFF_BY_CALC = os.path.join(DOSSIER_OUT, '%s_diff_qualif-prod.csv')  # %s = etude_dossier


logger.setLevel(logging.INFO)
t1 = time()


if PARSE_OTFA:
    fichier_otfa = FichierOtfa('Conc', mode='r',
                               files={'otfa': os.path.join(DOSSIER, 'OTFA', 'Conc.otfa.xml')})
    fichier_otfa.read_otfa()
    df_runs = parse_otfa_runs(fichier_otfa, ETATREF_SCENARIO_PAR_AMENAGEMENT)
    write_csv(df_runs, OUT_CSV_RUNS_FILE)


if WRITE_DIFF_DATAFRAME:
    df_runs = pd.read_csv(OUT_CSV_RUNS_FILE, delimiter=CSV_DELIMITER)
    cols = ['etude_dossier', 'etude_basename', 'scenario', 'run_idx', 'run_id', 'exe_id']
    df_runs_unique = df_runs[cols].drop_duplicates()
    df_diff_stat = get_run_steady_results(os.path.join(DOSSIER, 'Conc'), df_runs_unique, COEUR_REFERENCE,
                                          out_csv_diff_by_calc=OUT_CSV_DIFF_BY_CALC)
    write_csv(df_diff_stat, OUT_CSV_DIFF_FILE)


# Graphique synthétique de type barplot des caractéristiques des runs
if PLOT_RUN_BARPLOT:
    # Read data to plot
    df_runs = pd.read_csv(OUT_CSV_RUNS_FILE, delimiter=CSV_DELIMITER)

    # Build a FacetGrid object with barplots
    sns.set_context('notebook', font_scale=1.5, rc={'lines.linewidth': 2.5})
    g = sns.FacetGrid(df_runs, row='variable', sharey='row', height=4, aspect=3)
    g = g.map(sns.barplot, 'etude_dossier', 'value', 'exe_id',
              # order=ETATREF_SCENARIO_PAR_AMENAGEMENT.keys(),
              # hue_order=CRUE10_EXE.keys(),
              palette="husl", errorbar=None)

    # Sets xlabels and ylabels from titles
    for i, axes in enumerate(g.axes[:, :]):
        for j, ax in enumerate(axes):
            variable_name = str(ax.get_title()).split(' = ')[1]
            if i == 0:  # first row
                ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.22),
                          ncol=len(CRUE10_EXE), fancybox=True, shadow=True)
            if i == (len(g.axes[:, 0]) - 1):  # last row
                ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
            else:
                ax.get_xaxis().set_visible(False)
            if j == 0:  # first column
                ax.set_ylabel(variable_name)
            ax.set_title("")

    g.savefig(OUT_CSV_RUNS_FILE.replace('.csv', '.png'))
    plt.close()


# Graphique synthétique de type barplot des différences avec la référence
if PLOT_DIFF_BARPLOT:
    # Read data to plot
    df_diff_stat = pd.read_csv(OUT_CSV_DIFF_FILE, delimiter=CSV_DELIMITER)
    df_diff_stat = df_diff_stat[df_diff_stat['exe_id'] != COEUR_REFERENCE]

    # Build a FacetGrid object with barplots
    g = sns.FacetGrid(df_diff_stat, row='variable', sharey='row', height=4, aspect=3)
    g = g.map(sns.barplot, 'etude_dossier', 'value', 'exe_id',
              order=ETATREF_SCENARIO_PAR_AMENAGEMENT.keys(), palette='husl')

    # Sets xlabels and ylabels from titles
    for i, axes in enumerate(g.axes[:, :]):
        for j, ax in enumerate(axes):
            variable_name = str(ax.get_title()).split(' = ')[1]
            if i == 0:  # first row
                ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.22),
                          ncol=len(CRUE10_EXE), fancybox=True, shadow=True)
            if i == (len(g.axes[:, 0]) - 1):  # last row
                ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
            else:
                ax.get_xaxis().set_visible(False)
            if j == 0:  # first column
                ax.set_ylabel(variable_name)
            ax.set_title("")

    g.savefig(OUT_CSV_DIFF_FILE.replace('.csv', '_barplot.png'))
    plt.close()


# Graphique par aménagement avec les boîtes à moustaches
if PLOT_BOXPLOT:
    for etude_dossier in ETATREF_SCENARIO_PAR_AMENAGEMENT.keys():
        csv_path = OUT_CSV_DIFF_BY_CALC % etude_dossier
        try:
            df_diff = pd.read_csv(csv_path, delimiter=';')
        except IOError as e:
            logger.error(e)
            continue

        g = sns.boxplot(x='id_calcul', y='diff', data=df_diff)
        g.set_xlabel(u"Numéro du calcul pseudo-permanent")
        g.set_ylabel(u"Différence qualif-prod")

        fig = g.get_figure()
        fig.set_size_inches(16.0, 6.0)
        fig.savefig(csv_path.replace('.csv', '.png'))
        plt.close()

t2 = time()
logger.info("=> Temps d'exécution = {}s".format(t2 - t1))
