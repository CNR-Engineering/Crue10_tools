import sys

from crue10.run import CrueRun
from crue10.utils import CrueError, logger


rcal_path = '../../crue10_examples/Etu_VS2015_conc/Runs/Sc_VS2013-dclt/R2016-03-25-10h53m35s/Mo_VS2013-dclt/VS2013_c10_dcnc1400.rcal.xml'
try:
    run = CrueRun(rcal_path)
    print(run.summary())

    print(run.emh_types)  # 'Noeud', 'Casier'...
    print(run.emh)  # EMH identifiers list for every EMH type
    print(run.variables)  # Variable identifiers list for every EMH type

    # Read a single *steady* calculation
    res_perm = run.get_res_perm('Cc_360m3-s')
    for emh_type, res in res_perm.items():
        print(emh_type)
        print(res)  # shape = (number of EMHs, number of variables)

    # Read results at locations for all steady calculations
    #   shape = (number of steady calculations, number of requested EMH)
    print(run.get_res_all_perm_var_at_emhs('Z', ['St_RET33.300', 'Nd_VRH8.500']))

    # Export steady calculations data
    run.export_calc_perm_as_csv('Etu_VS2015_conc_perms.csv')

    # Read a single *unsteady* calculation
    res_trans = run.get_res_trans('Cc_dcnc1400-5min')
    for emh_type, res in res_trans.items():
        print(emh_type)
        print(res)  # shape = (number of time steps, number of EMHs, number of variables)

    # Read results at locations for a single unsteady calculation
    #   shape = (number of time steps, number of requested EMHs)
    print(run.get_res_trans_var_at_emhs('Cc_dcnc1400-5min', 'Z', ['St_RET33.300', 'Nd_VRH8.500']))

    # Export unsteady calculations data
    run.export_calc_trans_as_csv('Etu_VS2015_conc_trans.csv')

except CrueError as e:
    logger.critical(e)
    sys.exit(1)
