"""
Lance un Run unique qui se nomme 'test' (s'il existe déjà il sera écrasé)
"""
import os.path

from crue10.etude import Etude


etude = Etude(os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc',
                           'Etu_BE2016_conc', 'Etu_BE2016_conc.etu.xml'))
etude.read_all()

scenario = etude.get_scenario_courant()

run = scenario.create_and_launch_new_run(etude, run_id="test", force=True)
print(run.get_all_traces())

etude.write_etu()
