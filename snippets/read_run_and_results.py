import os.path
import sys

from crue10.study import Study
from crue10.utils import CrueError, logger


etu_folder = '../../TatooineMesher_examples/VS2015/in/Etu_VS2015_conc'
try:
    study = Study(os.path.join(etu_folder, 'Etu_VS2003_Conc.etu.xml'))
    run = study.get_scenario('Sc_EtatsRef2015').get_run('R2019-04-16-14h09m19s')
    results = run.get_results()
    # It is also possible not to pass through a Study instance with:
    # from crue10.results import RunResults
    # results = RunResults(os.path.join(etu_folder, 'Runs', 'Sc_EtatsRef2015', 'R2019-04-16-14h09m19s',
    #                                   'Mo_VS2013_c10_octobre_2014', 'VS2013_c10_EtatsRef.rcal.xml'))
    print(results.summary())

    print(results.emh_types)  # 'Noeud', 'Casier'...
    print(results.emh)  # EMH identifiers list for every EMH type
    print(results.variables)  # Variable identifiers list for every EMH type

    # Read a single *steady* calculation
    res_perm = results.get_res_steady('Cc_360m3-s')
    for emh_type, res in res_perm.items():
        print(emh_type)
        print(res)  # shape = (number of EMHs, number of variables)

    # Read results at locations for all steady calculations
    #   shape = (number of steady calculations, number of requested EMH)
    print(results.get_res_all_steady_var_at_emhs('Z', ['St_RET33.300', 'Nd_VRH8.500']))

    # Create output folder if not existing
    out_folder = '../tmp/read_run'
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    # Export steady calculations data
    results.export_calc_steady_as_csv(os.path.join(out_folder, 'Etu_VS2015_conc_perms.csv'))

    # Read a single *unsteady* calculation
    res_unsteady = results.get_res_unsteady('Cc_Avr_2006')
    for emh_type, res in res_unsteady.items():
        print(emh_type)
        print(res)  # shape = (number of time steps, number of EMHs, number of variables)

    # Read results at locations for a single unsteady calculation
    #   shape = (number of time steps, number of requested EMHs)
    print(results.get_res_unsteady_var_at_emhs('Cc_Avr_2006', 'Z', ['St_RET33.300', 'Nd_VRH8.500']))

    # Export unsteady calculations data
    results.export_calc_unsteady_as_csv(os.path.join(out_folder, 'Etu_VS2015_conc_trans.csv'))

except CrueError as e:
    logger.critical(e)
    sys.exit(1)