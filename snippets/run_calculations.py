# coding: utf-8
"""
Lancement de calculs Crue10 en chaîne pour une analyse de sensibilité sur les coefficients de Strickler.
Dans cet exemple, 8 calculs sont lancés en chaîne en modifiant les coefficients de Strickler de manière homogène
de -20 à 20 points par pas de 5 points (seula la loi de type `FkSto` n'est pas modifiée)

Les lois de Strickler initiales sont stockés dans le scénario `scenario_ori`.
Le fichier etu.xml initial est écrasé à la fin de tous les traitements

Un graphique superposant les niveaux calculés au PR1 pour tous ces calculs permanent est réalisé à la fin du script.
"""
from copy import deepcopy
import matplotlib.pyplot as plt
import numpy as np
import os.path

from crue10.etude import Etude
from crue10.utils import logger


etude = Etude(os.path.join('..', '..', 'Crue10_examples', 'Etudes-tests',
                           'Etu_BE2016_conc', 'Etu_BE2016_conc.etu.xml'))
etude.read_all()

scenario = etude.get_scenario('Sc_BE2016_etatref')
scenario_ori = deepcopy(scenario)

for delta_strickler in np.arange(-20.0, 20.0, step=5.0):
    for idx_sm, sous_modele in enumerate(scenario.modele.liste_sous_modeles):
        for fk_id, loi_frottement in sous_modele.lois_frottement.items():
            if loi_frottement.type != 'FkSto':
                loi_frottement_ori = scenario_ori.modele.get_sous_modele(sous_modele.id).lois_frottement[fk_id]
                new_strickler = loi_frottement_ori.loi_Fk[:, 1] + delta_strickler
                loi_frottement.loi_Fk[:, 1] = new_strickler.clip(min=10.0)
                # print("Nouvelles valeurs de Strickler pour %s: %s" % (fk_id, loi_frottement.loi_Fk[:, 1]))

    if False:
        # With regular run identifiers
        run = scenario.create_and_launch_new_run(etude, force=True,
                                                 comment='Modif Strickler %f points' % delta_strickler)
    else:
        # With custom run identifiers
        run_id = 'Strickler_%i' % delta_strickler
        run = scenario.create_and_launch_new_run(etude, run_id=run_id, force=True,
                                                 comment='Modif Strickler %f points' % delta_strickler)
    logger.info(run)

etude.write_etu()

# Plot Z at PR1
for _, run in scenario.runs.items():
    results = run.get_results()
    values = results.get_res_all_steady_var_at_emhs('Z', ['St_RET113.600'])
    nb_calc_steady = values.shape[0]
    time_serie = np.arange(0, nb_calc_steady * 3600, step=3600)

    plt.plot(time_serie, values[:, 0], label=run.id)

plt.xlabel("Temps (s)")
plt.ylabel("Niveau d'eau au PR1 (mNGFO)")
plt.legend(loc='upper left')
plt.show()
