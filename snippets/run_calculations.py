"""
Lancement de calculs Crue10 en chaîne pour une analyse de sensibilité sur les coefficients de Strickler.
Dans cet exemple, 8 calculs sont lancés en chaîne en modifiant les coefficients de Strickler de manière homogène
de -20 à 20 points par pas de 5 points (seula la loi de type `FkSto` n'est pas modifiée)

Les lois de Strickler initiales sont stockés dans le scénario `scenario_ori`.
Le fichier etu.xml initial est écrasé à la fin de tous les traitements
"""
from copy import deepcopy
import numpy as np

from crue10.study import Study


study = Study('../crue10_examples/Etudes-tests/Etu_BE2016_conc/Etu_BE2016_conc.etu.xml')
study.read_all()

scenario = study.get_scenario('Sc_BE2016_etatref')
scenario_ori = deepcopy(scenario)

for delta_strickler in np.arange(-20.0, 20.0, step=5.0):
    for idx_sm, submodel in enumerate(scenario.model.submodels):
        for fk_id, friction_law in submodel.friction_laws.items():
            if friction_law.type != 'FkSto':
                friction_law_ori = scenario_ori.model.submodels[idx_sm].friction_laws[fk_id]
                new_strickler = friction_law_ori.loi_Fk[:, 1] + delta_strickler
                friction_law.loi_Fk[:, 1] = new_strickler.clip(min=10.0)
                # print("Nouvelles valeurs de Strickler pour %s: %s" % (fk_id, friction_law.loi_Fk[:, 1]))

    # With regular run identifiers
    # run_id = scenario.create_and_launch_new_run(study, comment='Modif Strickler %f points' % delta_strickler)

    # With custom run identifiers
    run_id = 'Strickler_%i' % delta_strickler
    scenario.create_and_launch_new_run(study, run_id=run_id, comment='Modif Strickler %f points' % delta_strickler)
    print(run_id)

study.write_etu()
