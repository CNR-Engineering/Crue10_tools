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

import numpy as np
import logging
import os.path

logger.setLevel(logging.INFO)


# Loi de pilotage SV (2019)
section_PR1 = 'St_RET75.700B'
section_PR2 = 'St_RET82.000'
QLimPR1 = 4600  # m3/s
Z_cible_PR1 = 128.20  # mNGFO
Z_cible_PR2 = 127.30  # mNGFO

ECART_MAX = 0.015  # m

VALEUR_MANOEUVRANT = 2  # FIXME: ça devrait être 0 mais Crue10 ne le sort pas...


def trouver_branche_barrage(sous_modele):
    for branche in sous_modele.get_liste_branches():
        if branche.type == 15:
            return branche
    raise ExceptionCrue10("Pas de branche 15 dans le modèle")


etude = Etude(os.path.join('..', '..', 'Crue10_examples',
                           'Etudes-tests', 'Etu_SV2019_Conc_Br15', 'Etu_SV2019_Conc.etu.xml'))
etude.read_all()

scenario = etude.get_scenario_courant()
scenario.remove_all_runs()

# Récupération de la branche 15
sous_modele = etude.get_sous_modele('Sm_SV2019_Conc_EtatRef')
branche_bararge = trouver_branche_barrage(sous_modele)
section_barrage = branche_bararge.get_section_amont().id
section_pilote = branche_bararge.section_pilote.id


# La première itération correspond à la consigne
q_pilote, z_barrage = branche_bararge.loi_QZam.T
z_barrage[:] = Z_cible_PR1
z_barrage[q_pilote > QLimPR1] = Z_cible_PR2
branche_bararge.set_loi_QZam(np.column_stack((q_pilote, z_barrage)))

i = 0
while True:
    run_id = 'Iter' + str(i)
    # Lancement du calcul
    run = scenario.create_and_launch_new_run(etude, run_id, force=True)
    print('Lecture du run %s' % run.id)

    # Exploitation des résultats
    try:
        results = run.get_results()
        if results.nb_errors > 0:
            raise ExceptionCrue10("Erreur pour le %s" % run)
    except ExceptionCrue10 as e:  #FIXME: un plantage du calcul ne devrait pas lever d'ExceptionCrue10?
        logger.critical("Erreur après lancement de la simu")
        logger.critical(e)
        break  # On arrête tout

    logger.info(results)
    z_PR1, z_PR2, z_barrage = results.get_res_all_steady_var_at_emhs('Z',
                                                                     [section_PR1, section_PR2, section_barrage]).T
    regime_barrage = results.get_res_all_steady_var_at_emhs('RegimeBarrage', [branche_bararge.id])[:, 0]
    q_pilote = results.get_res_all_steady_var_at_emhs('Q', [section_pilote])[:, 0]

    # Résultat
    z_res_at_PR = z_PR1
    z_res_at_PR[q_pilote > QLimPR1] = z_PR2[q_pilote > QLimPR1]

    # Cible (consigne)
    z_target_at_PR = np.ones(scenario.get_nb_calc_pseudoperm) * Z_cible_PR1
    z_target_at_PR[q_pilote > QLimPR1] = Z_cible_PR2

    # Calcul dz (résultat - cible) et application de ce dz à la loi de pilotage (par interpolation)
    dz = z_res_at_PR - z_target_at_PR
    dz[regime_barrage != VALEUR_MANOEUVRANT] = 0.0
    q_non_manoeuvrant = q_pilote[regime_barrage != VALEUR_MANOEUVRANT]
    if q_non_manoeuvrant.size > 0:
        q_debut_non_manoeuvrant = q_non_manoeuvrant[0]
    else:
        q_debut_non_manoeuvrant = float('inf')

    # Vérification du critère d'arrêt
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
