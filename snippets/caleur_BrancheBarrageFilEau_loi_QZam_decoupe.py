# coding: utf-8
"""
Calage de la loi QZam de la branche 15 (sans la branche elle-même!) par un processus itératif sur tous les calculs pseudo-permanents
La loi de la consigne QZam est affichée à la fin (même en cas de plantage).

Pré-requis :
- La branche BarrageFilEau ne doit pas exister dans le modèle
- Les variables suivantes sont obligatoires :
    - `Z` et `Q` aux sections

Méthodologie :
- Le scénario courant est utilisé et tous les précédents runs sont supprimés
- Les débits des ClimMs servent à discrétiser la loi QZam
- Le débit de pilotage est pris égal à la somme des débits positifs (ie entrants) des ClimMs
    (attention cette hypothèse peut être fausse en fonction de la position des affluents)
- La consigne est appliquée au début à l'amont barrage puis l'écart de niveau (calculé - consigne) au PR est ajouté
    jusqu'à ce que l'écart maxmimum soit inférieur à un seuil (fixé à 1cm dans l'exemple).
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
                          'Etudes-tests', 'Etu_SV2019_Conc_Br15_decoupe', 'Etu_SV2019_Conc.etu.xml')
ECART_MAX = 0.01  # Différence de niveau (en m) maximale utilisée comme critère d'arrêt

noeud_amont_barrage = 'Nd_AMBSV82.750'
section_amont_barrage = 'St_AMBSV82.750'

# Consigne de SV (2019)
section_PR1 = 'St_RET75.700B'
section_PR2 = 'St_RET82.000'
QLimPR1 = 4600  # m3/s
# Lois de pilotage pour les 2 PR = tableaux avec les couples de valeurs : débit de pilotage (en m3/s) et niveau (en mNGFO)
Z_cible_PR1 = np.array([(0, 128.20), (QLimPR1, 128.20)])
Z_cible_PR2 = np.array([(QLimPR1, 127.20), (8000, 127.20)])  # la dernière cote est utilisée pour l'extrapolation


def is_strictly_increasing(array):
    return np.all(array[1:] > array[:-1])


def interp_target_PR(q_array):
    z_target_at_PR = np.interp(q_array, Z_cible_PR1[:, 0], Z_cible_PR1[:, 1], left=np.nan, right=np.nan)
    z_PR2 = np.interp(q_array, Z_cible_PR2[:, 0], Z_cible_PR2[:, 1], left=np.nan)
    z_target_at_PR[q_array > QLimPR1] = z_PR2[q_array > QLimPR1]
    return z_target_at_PR


def interp_target_PR_float(q_float):
    return interp_target_PR(np.array([q_float]))[0]


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

    # La première itération correspond à la consigne appliquée à l'amont barrage
    q_pilote = []
    z_imp_prev = []
    for calcul in scenario.get_liste_calc_pseudoperm(ignore_inactive=True):
        q = calcul.get_somme_positive_Qapp()
        q_pilote.append(q)
        z_imp = interp_target_PR_float(q)
        z_imp_prev.append(z_imp)
        calcul.set_valeur(noeud_amont_barrage, z_imp)
    q_pilote = np.array(q_pilote)
    z_imp_prev = np.array(z_imp_prev)
    assert is_strictly_increasing(q_pilote)

except ExceptionCrue10 as e:
    logger.critical(e)
    exit(1)
    raise RuntimeError  # only for IDE


df_lois = pd.DataFrame({'label': [], 'position': [], 'q_pilotage': [], 'z': []})
i = 0
while True:
    run_id = 'Iter' + str(i)

    try:
        # Ecriture du scénario pour conserver la loi calée dans le scénario courant
        scenario.write_all(etude.folder, folder_config=etude.folders['CONFIG'])

        # Lancement du calcul
        run = scenario.create_and_launch_new_run(etude, run_id, force=True)

        # Ecriture dans l'étude du nouveau run
        etude.write_etu()

        # Lecture du Run (traces et résultats disponibles)
        logger.info('Lecture du Run `%s`' % run.id)
        if run.nb_erreurs() > 0:
            logger.error(run.get_all_traces_above_warn())
            raise ExceptionCrue10("Erreur bloquante pour le %s" % run)
        resultats = run.get_resultats_calcul()
        logger.info(resultats)

    except ExceptionCrue10 as e:
        logger.critical(e)
        break

    z_PR1, z_PR2, z_barrage = resultats.get_res_all_steady_var_at_emhs(
        'Z', [section_PR1, section_PR2, section_amont_barrage]).T

    # Résultat
    z_res_at_PR = z_PR1
    z_res_at_PR[q_pilote > QLimPR1] = z_PR2[q_pilote > QLimPR1]

    # Cible (consigne)
    z_target_at_PR = interp_target_PR(q_pilote)

    # Ajout loi dans df_lois (pour le graphique ensuite)
    df_lois = df_lois.append(pd.DataFrame({'label': run_id, 'position': 'Amont barrage',
                                           'q_pilotage': q_pilote, 'z': z_barrage}),
                             ignore_index=True)
    df_lois = df_lois.append(pd.DataFrame({'label': run_id, 'position': 'PR',
                                           'q_pilotage': q_pilote, 'z': z_res_at_PR}),
                             ignore_index=True)

    # Vérification du critère d'arrêt
    dz = z_res_at_PR - z_target_at_PR
    txt = "Ecart: moyen=%f, max=%f" % (dz.mean(), dz.max())
    run.set_comment('Itération %i' % i + ': ' + txt)
    logger.info(txt)
    if dz.max() < ECART_MAX:
        logger.info("=> Calage réussi avec succès !")
        break

    assert len(q_pilote) == len(z_imp_prev) == len(dz) == scenario.get_nb_calc_pseudoperm_actif()

    # Mise à jour de la cote imposée à l'amont barrage
    for j, calcul in enumerate(scenario.get_liste_calc_pseudoperm(ignore_inactive=True)):
        q = q_pilote[j]
        z_imp = z_imp_prev[j] - dz[j]
        calcul.set_valeur(noeud_amont_barrage, z_imp)
        z_imp_prev[j] = z_imp

    i += 1

etude.write_etu()

# Ajout de la consigne dans df_lois (pour le graphique ensuite)
df_lois = df_lois.append(pd.DataFrame({'label': 'CONSIGNE PR2', 'position': 'PR',
                                       'q_pilotage': Z_cible_PR1[:, 0], 'z': Z_cible_PR1[:, 1]}), ignore_index=True)
df_lois = df_lois.append(pd.DataFrame({'label': 'CONSIGNE PR1', 'position': 'PR',
                                       'q_pilotage': Z_cible_PR2[:, 0], 'z': Z_cible_PR2[:, 1]}), ignore_index=True)

# Affichage de la loi (même si plantage avant) pour copier-coller dans Fudaa-Crue
for q, z_imp in zip(q_pilote, z_imp_prev):
    print(str(q) + '\t' + str(z_imp))

# Mise en graphique des résultats
ax = sns.lineplot(x='q_pilotage', y='z',
                  hue='label', style='position',
                  markers=True, dashes=False, data=df_lois)
ax.set_xlabel('Débit de pilotage [m3/s]')
ax.set_ylabel('Niveau [mNGFO]')

plt.legend(loc='lower left')
plt.show()
