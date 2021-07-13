# coding: utf-8
"""
Statistiques sur les caractéristiques et paramètres des modèles Conc

Beware: compatibility with Python 2 is not tested for figures (at least you have to replace `height` argument by `size`)
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
from _params import ETATREF_SCENARIO_PAR_AMENAGEMENT


DOSSIER = os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc')
WRITE_DATAFRAMES, PLOT_BARPLOT, PLOT_BOXPLOT = True, True, True

# Nommage des fichiers de sortie du script
OUT_CSV_STAT_FILE = '../tmp/stat_params_Conc/stat_modeles_Conc.csv'
OUT_CSV_MULTISTAT_FILE = '../tmp/stat_params_Conc/multi-stat_modeles_Conc.csv'


if WRITE_DATAFRAMES:
    df_stats = pd.DataFrame({'etude_dossier': [], 'variable': [], 'value': []})
    df_multi_stats = pd.DataFrame({'etude_dossier': [], 'variable': [], 'value': []})
    for folder in glob(os.path.join(DOSSIER, '*')):
        etude_dossier = os.path.basename(folder)

        def ajouter_values(etude_dossier, variable, values):
            global df_multi_stats
            for value in values:
                df_append = pd.Series({
                    'etude_dossier': etude_dossier, 'variable': variable, 'value': value
                })
                df_multi_stats = df_multi_stats.append(df_append, ignore_index=True)

        for etu_path in glob(os.path.join(folder, '*.etu.xml')):  # FIXME: only one etu.xml should be found by folder!
            if etude_dossier not in ETATREF_SCENARIO_PAR_AMENAGEMENT:
                logger.error("Le dossier `%s` n'a pas de scénario spécifié et ne sera pas traité"
                             % etude_dossier)
                continue

            etude = Etude(etu_path)
            etude.read_all()

            if ETATREF_SCENARIO_PAR_AMENAGEMENT[etude_dossier] is None:
                nom_scenario = etude.nom_scenario_courant
            else:
                nom_scenario = ETATREF_SCENARIO_PAR_AMENAGEMENT[etude_dossier]
            scenario = etude.get_scenario(nom_scenario)
            modele = scenario.modele

            values = OrderedDict([
                ('nb_noeuds', len(modele.get_liste_noeuds())),
                ('nb_sections', len(modele.get_liste_sections())),
                ('nb_casiers', len(modele.get_liste_casiers())),
                ('nb_branches', len(modele.get_liste_branches())),
                # ('theta_preissman', scenario.modele.get_theta_preissmann()),
                ('NbrPdtDecoup', modele.get_pnum_CalcPseudoPerm_NbrPdtDecoup()),
                ('NbrPdtMax', modele.get_pnum_CalcPseudoPerm_NbrPdtMax()),
                ('TolMaxZ', modele.get_pnum_CalcPseudoPerm_TolMaxZ()),
                ('TolMaxQ', modele.get_pnum_CalcPseudoPerm_TolMaxQ()),
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
                ajouter_values(etude_dossier, 'brange_bge_coefD', branche_bge_coefD)
            except ExceptionCrue10 as e:
                logger.warning(e)

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
            ajouter_values(etude_dossier, 'branche_seuil_largeur', branche_seuil_largeur)
            ajouter_values(etude_dossier, 'branche_seuil_coeff', branche_seuil_coeff)
            ajouter_values(etude_dossier, 'branche_seuil_isborda', branche_seuil_isborda)
            if nb_branche_seuil > 0:
                values['pourcentage_seuil_borda'] = nb_branche_seuil_avec_pdc_borda/nb_branche_seuil

            for var, value in values.items():
                df_append = pd.Series({
                    'etude_dossier': etude_dossier, 'variable': var, 'value': value,
                })
                df_stats = df_stats.append(df_append, ignore_index=True)

    df_stats.to_csv(OUT_CSV_STAT_FILE, sep=';', index=False)
    df_multi_stats.to_csv(OUT_CSV_MULTISTAT_FILE, sep=';', index=False)


if PLOT_BARPLOT:
    df_stats = pd.read_csv(OUT_CSV_STAT_FILE, delimiter=';')

    # Build a FacetGrid object with barplots
    sns.set_context("notebook", font_scale=1.5, rc={"lines.linewidth": 2.5})
    g = sns.FacetGrid(df_stats, row="variable", sharex=True, sharey=False, height=4, aspect=3)
    g = g.map(sns.barplot, "etude_dossier", "value", palette="husl",
              order=ETATREF_SCENARIO_PAR_AMENAGEMENT.keys(), ci=None)

    # Sets ylabels from titles
    for ax in g.axes[:, 0]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
        text = str(ax.get_title()).split(' = ')[1]
        ax.set_ylabel(text)
        ax.set_title("")

    g.set_xlabels(u"Aménagement (amont vers aval)")

    g.savefig(OUT_CSV_STAT_FILE.replace('.csv', '.png'))
    plt.close()


if PLOT_BOXPLOT:
    df_multi_stats = pd.read_csv(OUT_CSV_MULTISTAT_FILE, delimiter=';')

    # Build a FacetGrid object with boxplots
    sns.set_context("notebook", font_scale=1.5, rc={"lines.linewidth": 2.5})
    g = sns.FacetGrid(df_multi_stats, row="variable", sharex=True, sharey=False, height=3, aspect=4)
    g = g.map(sns.boxplot, "etude_dossier", "value", palette="husl", order=ETATREF_SCENARIO_PAR_AMENAGEMENT.keys())

    # Sets ylabels from titles
    for ax in g.axes[:, 0]:
        ax.set_xticklabels(ax.get_xticklabels(), rotation=90)
        text = str(ax.get_title()).split(' = ')[1]
        ax.set_ylabel(text)
        ax.set_title("")

    g.set_xlabels(u"Aménagement (amont vers aval)")

    g.savefig(OUT_CSV_MULTISTAT_FILE.replace('.csv', '.png'))
    plt.close()
