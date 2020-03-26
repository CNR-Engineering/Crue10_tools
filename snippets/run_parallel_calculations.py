# coding: utf-8
"""
Lancement de calculs Crue10 en parallèle pour une analyse de sensibilité sur les coefficients de Strickler.
Dans cet exemple, 8 calculs sont lancés en modifiant les coefficients de Strickler de manière homogène
de -20 à 20 points par pas de 5 points (seule la loi de type `FkSto` n'est pas modifiée)

Le fichier etu.xml initial est écrasé à la fin de tous les traitements.

Un graphique superposant les niveaux calculés au PR1 pour tous ces calculs permanent est réalisé à la fin du script.
"""
import matplotlib.pyplot as plt
import numpy as np
import os.path
from time import perf_counter

from crue10.etude import Etude
from crue10.utils import logger
from crue10.utils.multiple_runs import launch_scenario_modifications


etude = Etude(os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc',
                           'Etu_BE2016_conc', 'Etu_BE2016_conc.etu.xml'))
etude.read_all()

scenario = etude.get_scenario('Sc_BE2016_etatref')
scenario.remove_all_runs(sleep=1.0)


# Build list of modifications
modifications_liste = []
for i, delta_strickler in enumerate(np.arange(-20.0, 20.0, step=5.0)):
    modifications = {'run_id': 'Iter%i' % i}
    for loi_frottement in scenario.modele.get_liste_lois_frottement(ignore_sto=True):
        fk_id = loi_frottement.id
        loi_frottement = scenario.modele.get_loi_frottement(fk_id)
        new_strickler = max(loi_frottement.loi_Fk[0, 1] + delta_strickler, 10.0)
        modifications[fk_id] = new_strickler
    modifications_liste.append(modifications)


# Get the modification function
def apply_modifications(modifications):
    return scenario.get_function_apply_modifications(etude)(modifications)


if __name__ == '__main__':
    # Performs a parallel computation
    t1 = perf_counter()
    runs_liste = launch_scenario_modifications(apply_modifications, modifications_liste)
    t2 = perf_counter()
    logger.info("=> Temps d'exécution = {}s".format(t2 - t1))

    # Write a clean etu.xml file
    for run in runs_liste:
        scenario.add_run(run)
    scenario.set_current_run_id(runs_liste[-1].id)
    etude.write_etu()

    # Plot Z at PR1
    for run in runs_liste:
        results = run.get_results()
        values = results.get_res_all_steady_var_at_emhs('Z', ['St_RET113.600'])
        nb_calc_steady = values.shape[0]
        time_serie = np.arange(1, nb_calc_steady + 1, step=1)
        plt.plot(time_serie, values[:, 0], label=run.id)

    plt.xlabel(u"Numéro du calcul pseudo-permanent")
    plt.ylabel(u"Niveau d'eau au PR1 [mNGFO]")
    plt.legend(loc='upper left')
    plt.show()
