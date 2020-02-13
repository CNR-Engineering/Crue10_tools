# coding: utf-8
"""
Statistiques sur les caractéristiques et paramètres des modèles Conc
"""
from collections import OrderedDict
from glob import glob
import os
import pandas as pd
from matplotlib import pyplot as plt
import numpy as np
import seaborn as sns

from crue10.emh.branche import BrancheBarrageFilEau, BrancheSeuilTransversal, BrancheSeuilLateral
from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger


WRITE_DATAFRAMES, PLOT_BARPLOTS, PLOT_BOXPLOT = True, True, True

OUT_CSV_STAT_FILE = '../tmp/stat_params_Conc/stat_modeles_Conc.csv'
OUT_CSV_MULTISTAT_FILE = '../tmp/stat_params_Conc/multi-stat_modeles_Conc.csv'


SCENARIO_PAR_AMENAGEMENT = OrderedDict([
    # Scénario à utiliser par aménagement s'il diffère du "scénario courant" (sinon mettre `None`)
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

# Filtre sur les aménagements voulus
# SCENARIO_PAR_AMENAGEMENT = {amenagement: SCENARIO_PAR_AMENAGEMENT[amenagement] for amenagement in ['AV', 'VA']}


if WRITE_DATAFRAMES:
    df_stats = pd.DataFrame({'amenagement': [], 'variable': [], 'value': []})
    df_multi_stats = pd.DataFrame({'amenagement': [], 'variable': [], 'value': []})
    for folder in glob(os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc', '*')):
        amenagement = os.path.basename(folder)[4:6]
        if amenagement not in SCENARIO_PAR_AMENAGEMENT:
            continue
        print(amenagement)

        def ajouter_values(amenagement, variable, values):
            global df_multi_stats
            for value in values:
                df_append = pd.Series({
                    'amenagement': amenagement, 'variable': variable, 'value': value
                })
                df_multi_stats = df_multi_stats.append(df_append, ignore_index=True)

        for etu_path in glob(os.path.join(folder, '*.etu.xml')):
            etude = Etude(etu_path)
            etude.read_all()

            if SCENARIO_PAR_AMENAGEMENT[amenagement] is None:
                nom_scenario = etude.nom_scenario_courant
            else:
                nom_scenario = SCENARIO_PAR_AMENAGEMENT[amenagement]
            scenario = etude.get_scenario(nom_scenario)
            modele = scenario.modele

            values = OrderedDict([
                ('nb_noeuds', len(modele.get_liste_noeuds())),
                ('nb_sections', len(modele.get_liste_sections())),
                ('nb_casiers', len(modele.get_liste_casiers())),
                ('nb_branches', len(modele.get_liste_branches())),
                # ('theta_preissman', scenario.modele.get_theta_preissmann()),
                ('debit_max_calculs_pseudoperm',
                 max([calcul.get_somme_positive_Qapp() for calcul in scenario.get_liste_calc_pseudoperm()]))
            ])

            # Branche barrage
            branche_bge_coefD = []
            try:
                branche_bararge = modele.get_branche_barrage()
                if isinstance(branche_bararge, BrancheBarrageFilEau):
                    branche_bge_coefD += list(branche_bararge.liste_elements_seuil[:, 2])
                    assert len(np.unique(branche_bararge.liste_elements_seuil[:, 1])) == 1  # same elevation for all passes
                ajouter_values(amenagement, 'brange_bge_coefD', branche_bge_coefD)
            except ExceptionCrue10 as e:
                logger.warn(e)

            # Branche seuils
            nb_branche_seuil = 0
            nb_branche_seuil_avec_pdc_borda = 0
            branche_seuil_largeur = []
            branche_seuil_coeff = []
            branche_seuil_isborda = []
            for branche in modele.get_liste_branches():
                if isinstance(branche, BrancheSeuilLateral) or isinstance(branche, BrancheSeuilTransversal):
                    nb_branche_seuil += 1
                    if branche.formule_pertes_de_charge == 'Borda':
                        nb_branche_seuil_avec_pdc_borda += 1
                    branche_seuil_largeur += list(branche.liste_elements_seuil[:, 0])
                    branche_seuil_coeff += list(branche.liste_elements_seuil[:, 2] * branche.liste_elements_seuil[:, 3])
            ajouter_values(amenagement, 'branche_seuil_largeur', branche_seuil_largeur)
            ajouter_values(amenagement, 'branche_seuil_coeff', branche_seuil_coeff)
            ajouter_values(amenagement, 'branche_seuil_isborda', branche_seuil_isborda)
            if nb_branche_seuil > 0:
                values['pourcentage_seuil_borda'] = nb_branche_seuil_avec_pdc_borda/nb_branche_seuil

            for var, value in values.items():
                df_append = pd.Series({
                    'amenagement': amenagement, 'variable': var, 'value': value,
                })
                df_stats = df_stats.append(df_append, ignore_index=True)

    df_stats.to_csv(OUT_CSV_STAT_FILE, sep=';', index=False)
    df_multi_stats.to_csv(OUT_CSV_MULTISTAT_FILE, sep=';', index=False)


if PLOT_BARPLOTS:
    df_stats = pd.read_csv(OUT_CSV_STAT_FILE, delimiter=';')

    # Build a FacetGrid object with barplots
    sns.set_context("notebook", font_scale=1.5, rc={"lines.linewidth": 2.5})
    g = sns.FacetGrid(df_stats, row="variable", sharex=True, sharey=False, size=3, aspect=4)
    g = g.map(sns.barplot, "amenagement", "value", palette="husl", order=SCENARIO_PAR_AMENAGEMENT.keys(), ci=None)

    # Sets ylabels from titles
    for ax in g.axes[:, 0]:
        text = str(ax.get_title()).split(' = ')[1]
        ax.set_ylabel(text)
        ax.set_title("")

    g.set_xlabels(u"Aménagement (amont vers aval)")

    g.savefig(OUT_CSV_STAT_FILE.replace('.csv', '.png'))
    plt.close()


if PLOT_BOXPLOT:
    df_multi_stats = pd.read_csv(OUT_CSV_MULTISTAT_FILE, delimiter=';')

    # Build a FacetGrid object with barplots
    sns.set_context("notebook", font_scale=1.5, rc={"lines.linewidth": 2.5})
    g = sns.FacetGrid(df_multi_stats, row="variable", sharex=True, sharey=False, size=3, aspect=4)
    g = g.map(sns.boxplot, "amenagement", "value", palette="husl", order=SCENARIO_PAR_AMENAGEMENT.keys())

    # Sets ylabels from titles
    for ax in g.axes[:, 0]:
        text = str(ax.get_title()).split(' = ')[1]
        ax.set_ylabel(text)
        ax.set_title("")

    g.set_xlabels(u"Aménagement (amont vers aval)")

    g.savefig(OUT_CSV_MULTISTAT_FILE.replace('.csv', '.png'))
    plt.close()
