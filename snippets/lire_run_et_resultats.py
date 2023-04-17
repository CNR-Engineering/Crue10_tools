# coding: utf-8
import os.path
import sys

from crue10.etude import Etude
from crue10.run import Run
from crue10.utils import ExceptionCrue10, logger


etu_folder = '../../TatooineMesher_examples/VS2015/in/Etu_VS2015_conc'
try:
    etude = Etude(os.path.join(etu_folder, 'Etu_VS2003_Conc.etu.xml'))
    run = etude.get_scenario_courant().get_last_run()

    # Affichage de quelques traces
    logger.info('AVERTISSEMENTS ET ERREURS DU CALCUL:\n' + run.get_all_traces(services=['c'], gravite_min='WARN'))

    # Calcul du temps total (sommé par les valeurs fournies dans les traces)
    time_list = [run.get_time(services=[service]) for service in Run.SERVICES]
    logger.info('Temps calcul Crue = %f s (' % sum(time_list) + ' + '.join([str(time) for time in time_list]) + ')')

    logger.info(run)

    resultats = run.get_resultats_calcul()
    # It is also possible to avoid using the Etude instance, in providing the path rcal to ResultatsCalcul:
    # from crue10.resultats import ResultatsCalcul
    # resultats = ResultatsCalcul(os.path.join(etu_folder, 'Runs', 'Sc_EtatsRef2015', 'R2019-04-16-14h09m19s',
    #                                        'Mo_VS2013_c10_octobre_2014', 'VS2013_c10_EtatsRef.rcal.xml'))
    print(resultats.summary())

    print(resultats.emh_types)  # 'Noeud', 'Casier'...
    print(resultats.emh)  # EMH identifiers list for every EMH type
    print(resultats.variables)  # Variable identifiers list for every EMH type

    # Read a single *steady* calculation
    res_perm = resultats.get_data_pseudoperm('Cc_360m3-s')
    for emh_type, res in res_perm.items():
        print(emh_type)
        print(res)  # shape = (number of EMHs, number of variables)

    # Read results at locations for all steady calculations
    #   shape = (number of steady calculations, number of requested EMH)
    print(resultats.get_res_all_pseudoperm_var_at_emhs('Z', ['St_RET33.300', 'Nd_VRH8.500']))

    # Create output folder if not existing
    out_folder = '../tmp/read_run'
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    # Export steady calculations data
    resultats.write_all_calc_pseudoperm_in_csv(os.path.join(out_folder, 'Etu_VS2015_conc_perms.csv'))

    # Read a single *unsteady* calculation
    res_trans = resultats.get_data_trans('Cc_Avr_2006')
    for emh_type, res in res_trans.items():
        print(emh_type)
        print(res)  # shape = (number of time steps, number of EMHs, number of variables)

    # Read results at locations for a single unsteady calculation
    #   shape = (number of time steps, number of requested EMHs)
    print(resultats.get_res_trans_var_at_emhs('Cc_Avr_2006', 'Z', ['St_RET33.300', 'Nd_VRH8.500']))

    # Export unsteady calculations data
    resultats.write_all_calc_trans_in_csv(os.path.join(out_folder, 'Etu_VS2015_conc_trans.csv'))

except ExceptionCrue10 as e:
    logger.critical(e)
    sys.exit(1)
