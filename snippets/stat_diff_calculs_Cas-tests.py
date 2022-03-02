# coding: utf-8
"""
Statistiques sur les résulats des cas de validation du code Crue10 (tous les scénarios)

Beware: compatibility with Python 2 is not tested for figures (at least you have to replace `height` argument by `size`)
"""
import logging
import os
import pandas as pd
from matplotlib import pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import numpy as np
import seaborn as sns
from time import time

from crue10.utils import logger
from crue10.utils.multiple_runs import get_run_steady_results, launch_runs
from _params import CRUE10_EXE, CRUE10_EXE_REFERENCE, CSV_DELIMITER, write_csv


DOSSIER = os.path.join('..', '..', 'Crue10_examples', 'Cas-tests')
RUN_CALCULATIONS, WRITE_DIFF_DATAFRAME, PLOT_RUN_BARPLOT, PLOT_DIFF_BARPLOT, PLOT_DIFF_HEATMAP = \
    True, True, True, True, True
CRUE10_EXE_HEATMAP = 'qualif'

# Nommage des fichiers de sortie du script
OUT_CSV_RUNS_FILE = '../tmp/stat_calculs_Cas-tests/bilan_runs.csv'
OUT_CSV_DIFF_FILE = '../tmp/stat_calculs_Cas-tests/bilan_stat_diff.csv'


logger.setLevel(logging.INFO)
t1 = time()


if RUN_CALCULATIONS:
    df_runs = launch_runs(DOSSIER, None, CRUE10_EXE, overwrite=True)
    write_csv(df_runs, OUT_CSV_RUNS_FILE)


if WRITE_DIFF_DATAFRAME:
    df_runs = pd.read_csv(OUT_CSV_RUNS_FILE, delimiter=CSV_DELIMITER)
    cols = ['etude_dossier', 'etude_basename', 'scenario', 'run_idx', 'run_id', 'exe_id']
    df_runs_unique = df_runs[cols].drop_duplicates()
    df_diff_stat = get_run_steady_results(DOSSIER, df_runs_unique, CRUE10_EXE_REFERENCE)
    write_csv(df_diff_stat, OUT_CSV_DIFF_FILE)


# Graphique synthétique de type barplot des caractéristiques des runs
if PLOT_RUN_BARPLOT:
    # Read data to plot
    df_runs = pd.read_csv(OUT_CSV_RUNS_FILE, delimiter=CSV_DELIMITER)
    df_runs = df_runs.sort_values(by='scenario')

    # Filter data
    # df_runs = df_runs.loc[df_runs['exe_id'] != 'local', :]
    df_runs = df_runs.loc[df_runs['variable'] == 'nb_services_ok', :]

    # Build a FacetGrid object with barplots
    sns.set_context('notebook', font_scale=1.5, rc={'lines.linewidth': 2.5})
    # g = sns.FacetGrid(df_runs, row='variable', col='etude_dossier', sharex=False, sharey='row', height=4, aspect=2)
    g = sns.FacetGrid(df_runs, row='variable', sharey='row', height=4, aspect=25)
    g = g.map(sns.barplot, 'scenario', 'value', 'exe_id',
              hue_order=CRUE10_EXE.keys(), palette="husl", ci=None)

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
    df_diff_stat = df_diff_stat[df_diff_stat['exe_id'] != CRUE10_EXE_REFERENCE]
    # df_diff_stat = df_diff_stat[df_diff_stat['scenario'] != 'Sc_AV2011_c10']
    # df_diff_stat = df_diff_stat[df_diff_stat['scenario'] != 'Sc_M31-4_c10']
    df_diff_stat = df_diff_stat.sort_values(by='scenario')

    # Build a FacetGrid object with barplots
    g = sns.FacetGrid(df_diff_stat, row='variable', sharey='row', height=2, aspect=25)
    g = g.map(sns.barplot, 'scenario', 'value', 'exe_id', palette="husl")

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


# Graphique synthétique de type heatmap des différences avec la référence
if PLOT_DIFF_HEATMAP:
    # Read data to plot
    df_diff_stat = pd.read_csv(OUT_CSV_DIFF_FILE, delimiter=CSV_DELIMITER)
    df_diff_stat = df_diff_stat[df_diff_stat['exe_id'] == CRUE10_EXE_HEATMAP]
    df_diff_stat = df_diff_stat.sort_values(by='scenario')

    # Build a FacetGrid object
    g = sns.FacetGrid(df_diff_stat, row='variable', sharey='row', height=2, aspect=25)
    fig = g.fig

    def draw_heatmap(*args, **kwargs):
        data = kwargs.pop('data')
        data_wide = data.pivot(index=args[1], columns=args[0], values=args[2])
        if np.unique(data[args[1]]) == 'MSD':
            cmap = 'coolwarm'
            vabs_max = np.abs(data[args[2]]).max()
            vmin = -vabs_max
            vmax = vabs_max
            sns.heatmap(data_wide, cmap=cmap, vmin=vmin, vmax=vmax, **kwargs)
        else:
            cmap = 'Reds'
            sns.heatmap(data_wide, cmap=cmap, **kwargs)
    g.map_dataframe(draw_heatmap, 'scenario', 'variable', 'value', square=True,
                    cbar=False  # cbar is secustomized and set after
    )

    # Sets xlabels and ylabels from titles
    for i, axes in enumerate(g.axes[:, :]):
        for j, ax in enumerate(axes):
            variable_name = str(ax.get_title()).split(' = ')[1]
            if i == (len(g.axes[:, 0]) - 1):  # last row
                ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
            else:
                ax.get_xaxis().set_visible(False)
            ax.set_ylabel("")
            ax.set_title("")

            # Add a custom colobar
            mappable = ax.collections[0]
            divider = make_axes_locatable(ax)
            cax = divider.append_axes('top', size='60%', pad=0.2, aspect=1.0/80.0)
            fig.colorbar(mappable, cax=cax, orientation='horizontal')
            cax.xaxis.set_ticks_position('top')

    g.savefig(OUT_CSV_DIFF_FILE.replace('.csv', '_heatmap.png'))
    plt.close()


t2 = time()
logger.info("=> Temps d'exécution = {}s".format(t2 - t1))
