# coding: utf-8
import fiona
import os
from shapely.geometry import mapping
import sys

from crue10.etude import Etude
from crue10.utils import CrueError, logger


try:
    # Read modele
    model_folder = '../../TatooineMesher_examples/VS2015/in/Etu_VS2015_conc'
    study = Etude(os.path.join(model_folder, 'Etu_VS2003_Conc.etu.xml'))
    modele = study.get_modele('Mo_VS2013_c10_octobre_2014')
    modele.read_all()

    # Read rcal result file and its results
    run = study.get_scenario('Sc_EtatsRef2015').get_run('R2019-04-16-14h09m19s')
    results = run.get_results()
    calc_name = 'Cc_Avr_2006'

    pos_Q = results.variables['Section'].index('Q')
    calc_trans = results.get_calc_unsteady(calc_name)
    Q_at_sections = results.get_res_unsteady(calc_name)['Section'][:, :, pos_Q]
    # print(Q_at_sections[:, run.emh['Section'].index('St_RET15.100')])
    Qmin_at_sections = Q_at_sections.min(axis=0)
    Qmax_at_sections = Q_at_sections.max(axis=0)

    # Write a shp file to check
    variables = ['Zseuil_min', 'Qmax', 'Qmin']
    schema = {
        'geometry': 'LineString',
        'properties': {'id_branche': 'str', **{var: 'str' for var in variables}}
    }
    with fiona.open(os.path.join(model_folder, 'check_at_branches.shp'), 'w', 'ESRI Shapefile', schema) as out_shp:
        for sous_modele in modele.liste_sous_modeles:
            sous_modele.convert_sectionidem_to_sectionprofil()
            print(sous_modele.summary())

            for branche in sous_modele.iter_on_branches():
                if branche.is_active:
                    values = {var: 'NA' for var in variables}

                    idx_section = results.emh['Section'].index(
                        branche.get_section_amont().id)  # same results for upstream and downstream sections
                    values['Qmin'] = round(Qmin_at_sections[idx_section], 0)
                    values['Qmax'] = round(Qmax_at_sections[idx_section], 0)

                    if branche.type in (2, 4):
                        values['Zseuil_min'] = branche.liste_elements_seuil.min(axis=0)[1]

                    layer = {
                        'geometry': mapping(branche.geom),
                        'properties': {
                            'id_branche': branche.id,
                            **values
                        }
                    }
                    out_shp.write(layer)

except CrueError as e:
    logger.critical(e)
    sys.exit(2)
