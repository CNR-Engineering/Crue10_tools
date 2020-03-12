# coding: utf-8
"""
Calage de la loi QZam de la branche 15 par un processus itératif sur tous les calculs pseudo-permanents

Méthodologie :
- Le scénario courant est utilisé et tous les précédents runs sont supprimés
- La consigne est appliquée au début dans la loi QZam puis l'écart de niveau (calculé - consigne) au PR est ajouté
    jusqu'à ce que l'écart maxmimum soit inférieur à un seuil (fixé à 1.5cm dans l'exemple).
- Pour les débits avec le barrage non manoeuvrant, la cote n'est plus actualisée
    et l'écart pour ces débits n'est pas pris en compte dans le critère d'arrêt
- Les débits de la loi QZam initiale sont conservés, sa discrétisation doit donc être correcte
- Un plantage lors d'un run (sur un des pseudo-permanents) arrête le processus brutalement
"""
from crue10.utils import ExceptionCrue10, logger
from crue10.etude import Etude

import logging
import matplotlib.pyplot as plt
import numpy as np
import os.path
import pandas as pd
import seaborn as sns
from sys import exit


logger.setLevel(logging.INFO)


# Chemin vers l'étude à traiter (le scénario courant sera utilisé)
ETUDE_PATH = os.path.join('..', '..', 'Crue10_examples',
                          'Etudes-tests', 'Etu_SV2019_Conc_Br15', 'Etu_SV2019_Conc.etu.xml')
ECART_MAX = 0.015  # Différence de niveau (en m) maximale utilisée comme critère d'arrêt

# Consigne de SV (2019)
section_PR1 = 'St_RET75.700B'
section_PR2 = 'St_RET82.000'
QLimPR1 = 4600  # m3/s
# Lois de pilotage pour les 2 PR = tableaux avec les couples de valeurs : débit (en m3/s) et niveau (en mGNFO)
Z_cible_PR1 = np.array([(0, 128.20), (4600, 128.20)])
Z_cible_PR2 = np.array([(4600, 127.30), (8000, 127.30)])  # la dernière cote est utilisée pour l'extrapolation


VALEUR_MANOEUVRANT = 2  # FIXME: ça devrait être 0 mais Crue10 ne le sort pas...


def interp_target_PR(q_array):
    z_target_at_PR = np.interp(q_array, Z_cible_PR1[:, 0], Z_cible_PR1[:, 1], left=np.nan, right=np.nan)
    z_PR2 = np.interp(q_array, Z_cible_PR2[:, 0], Z_cible_PR2[:, 1], left=np.nan)
    z_target_at_PR[q_array > QLimPR1] = z_PR2[q_array > QLimPR1]
    return z_target_at_PR


# Vérification consigne
def check_chronique(array, id_PR):
    if not np.all(array[1:, 0] >= array[:-1, 0]):
        raise ExceptionCrue10("La chronique de débit pour le PR%i n'est pas strictement croissante" % id_PR)
    if id_PR == 1:
        if array[:, 0][0] > 0:
            raise ExceptionCrue10("La chronique de débit pour le PR%i doit commencer à 0" % id_PR)
        if array[:, 0][-1] < QLimPR1:
            raise ExceptionCrue10("La chronique de débit pour le PR%i doit aller jusqu'à QLimPR1" % id_PR)
    elif id_PR == 2:
        if array[:, 0][0] > QLimPR1:
            raise ExceptionCrue10("La chronique de débit pour le PR%i doit commencer au moins à QLimPR1" % id_PR)


check_chronique(Z_cible_PR1, 1)
check_chronique(Z_cible_PR2, 2)

try:
    etude = Etude(ETUDE_PATH)
    etude.read_all()

    scenario = etude.get_scenario_courant()
    scenario.remove_all_runs()

    # Récupération de la branche 15
    branche_bararge = scenario.modele.get_branche_barrage()
    section_barrage = branche_bararge.get_section_amont().id
    section_pilote = branche_bararge.section_pilote.id

    # La première itération correspond à la consigne appliquée à l'amont barrage
    q_pilote, _ = branche_bararge.loi_QZam.T
    z_barrage = interp_target_PR(q_pilote)
    branche_bararge.set_loi_QZam(np.column_stack((q_pilote, z_barrage)))

except ExceptionCrue10 as e:
    logger.critical(e)
    exit(1)
    raise RuntimeError  # only for IDE


df_lois = pd.DataFrame({'label': [], 'position': [], 'q_pilotage': [], 'z': []})
i = 0
while True:
    run_id = 'Iter' + str(i)

    try:
        # Lancement du calcul
        run = scenario.create_and_launch_new_run(etude, run_id, force=True)

        # Lecture du Run (traces et résultats disponibles)
        logger.info('Lecture du Run `%s`' % run.id)
        if run.nb_erreurs() > 0:
            logger.error(run.get_all_traces_above_warn())
            raise ExceptionCrue10("Erreur bloquante pour le %s" % run)
        results = run.get_results()
        logger.info(results)

    except ExceptionCrue10 as e:
        logger.critical(e)
        break

    z_PR1, z_PR2, z_barrage = results.get_res_all_steady_var_at_emhs('Z',
                                                                     [section_PR1, section_PR2, section_barrage]).T
    regime_barrage = results.get_res_all_steady_var_at_emhs('RegimeBarrage', [branche_bararge.id])[:, 0]
    q_pilote = results.get_res_all_steady_var_at_emhs('Q', [section_pilote])[:, 0]

    # Résultat
    z_res_at_PR = z_PR1
    z_res_at_PR[q_pilote > QLimPR1] = z_PR2[q_pilote > QLimPR1]

    # Cible (consigne)
    z_target_at_PR = interp_target_PR(q_pilote)

    # Calcul dz (résultat - cible) et application de ce dz à la loi de pilotage (par interpolation)
    q_non_manoeuvrant = q_pilote[regime_barrage != VALEUR_MANOEUVRANT]
    if q_non_manoeuvrant.size > 0:
        q_debut_non_manoeuvrant = q_non_manoeuvrant[0]
    else:
        q_debut_non_manoeuvrant = float('inf')

    # Ajout loi dans df_lois (pour le graphique ensuite)
    df_lois = df_lois.append(pd.DataFrame({'label': run_id, 'position': 'Amont barrage',
                                           'q_pilotage': q_pilote[regime_barrage == VALEUR_MANOEUVRANT],
                                           'z': z_barrage[regime_barrage == VALEUR_MANOEUVRANT]}),
                             ignore_index=True)
    df_lois = df_lois.append(pd.DataFrame({'label': run_id, 'position': 'PR',
                                           'q_pilotage': q_pilote[regime_barrage == VALEUR_MANOEUVRANT],
                                           'z': z_res_at_PR[regime_barrage == VALEUR_MANOEUVRANT]}),
                             ignore_index=True)

    # Vérification du critère d'arrêt
    dz = z_res_at_PR - z_target_at_PR
    dz_filtre = dz[regime_barrage == VALEUR_MANOEUVRANT]
    logger.info("Ecart: moyen=%f, max=%f, Qnon manoeuvrant=%f"
                % (dz_filtre.mean(), dz_filtre.max(), q_debut_non_manoeuvrant))
    if dz_filtre.max() < ECART_MAX:
        logger.info("=> Calage réussi avec succès !")
        break

    # Mise à jour de la cote dans la loi QZam
    if i == 0:
        z_consigne_prev = z_target_at_PR
    else:
        z_consigne_prev = np.interp(q_pilote, branche_bararge.loi_QZam[:, 0], branche_bararge.loi_QZam[:, 1])
    new_loi_QZam = np.column_stack((q_pilote, z_consigne_prev - dz))
    new_loi_QZam = new_loi_QZam[new_loi_QZam[:, 0].argsort(), :]
    branche_bararge.loi_QZam[:, 1] = np.interp(branche_bararge.loi_QZam[:, 0],
                                               new_loi_QZam[:, 0], new_loi_QZam[:, 1])

    i += 1

# Ecriture dans l'étude des runs du scénario courant
etude.write_etu()


# Ajout de la consigne dans df_lois (pour le graphique ensuite)
df_lois = df_lois.append(pd.DataFrame({'label': 'CONSIGNE PR2', 'position': 'PR',
                                       'q_pilotage': Z_cible_PR1[:, 0], 'z': Z_cible_PR1[:, 1]}), ignore_index=True)
df_lois = df_lois.append(pd.DataFrame({'label': 'CONSIGNE PR1', 'position': 'PR',
                                       'q_pilotage': Z_cible_PR2[:, 0], 'z': Z_cible_PR2[:, 1]}), ignore_index=True)

# Mise en graphique des résultats
ax = sns.lineplot(x='q_pilotage', y='z',
                  hue='label', style='position',
                  markers=True, dashes=False, data=df_lois)
ax.set_xlabel('Débit de pilotage [m3/s]')
ax.set_ylabel('Niveau [mNGFO]')

plt.legend(loc='lower left')
plt.show()
