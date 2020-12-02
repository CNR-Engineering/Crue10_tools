"""
Lance un Run unique qui se nomme 'test' (s'il existe déjà il sera écrasé)
"""
import os.path

from crue10.etude import Etude


etude = Etude(os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc',
                           'Etu_BE2016_conc', 'Etu_BE2016_conc.etu.xml'))
etude.read_all()

scenario = etude.get_scenario_courant()

# Méthode 1 : tous les services à la fois
run = scenario.create_and_launch_new_run(etude, run_id="test", force=True)
print(run.get_all_traces_above_warn())

# Méthode 2 : en séquançant le lancement des services
run = scenario.create_new_run(etude, run_id="test", force=True)
run.launch_services(['r', 'g', 'i'])
run.launch_services(['c'])
print(run.get_all_traces_above_warn())

etude.write_etu()
