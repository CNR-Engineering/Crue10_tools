# coding: utf-8
"""

Zf -> from geometry

TODO:
Z -> min(Zf, Z)
H <- Z - Zf
"""
from collections import OrderedDict
import fiona
import os.path
from shapely.geometry import mapping, Point
import sys

from crue10.emh.section import SectionProfil
from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger
from crue10.utils.settings import CSV_DELIMITER


ADD_BOTTOM = True
VARIABLES = ['Z', 'H', 'Fr']


etu_folder = '../../TatooineMesher_examples/VS2015/in/Etu_VS2015_conc'
try:
    # Get modele
    etude = Etude(os.path.join(etu_folder, 'Etu_VS2003_Conc.etu.xml'))
    modele = etude.get_scenario_courant().modele
    modele.read_all()
    for sous_modele in modele.liste_sous_modeles:
        sous_modele.convert_sectionidem_to_sectionprofil()
        print(sous_modele.summary())

    # Get a dict with active section bottom elevations
    bottom = OrderedDict()
    for section in modele.get_liste_sections():
        if section.is_active and isinstance(section, SectionProfil):
            bottom[section.id] = section.get_coord(add_z=True)

    # Read rcal result file
    scenario = etude.get_scenario('Sc_EtatsRef2015')
    run = scenario.get_last_run()
    results = run.get_results()
    print(results.summary())

    # Check result consistency
    missing_sections = modele.get_missing_active_sections(results.emh['Section'])
    if missing_sections:
        print("Missing sections:\n%s" % missing_sections)

    # Read a single *steady* calculation
    res_perm = results.get_res_steady('Cc_360m3-s')
    res = res_perm['Section']

    # Export a longitudinal profile between 2 nodes in CSV
    branches = modele.get_liste_branches_entre_deux_noeuds('Nd_CAF4.000', 'Nd_RET33.700')
    df_res = results.get_res_steady_at_sections_along_branches_as_dataframe('Cc_360m3-s', branches, VARIABLES)
    df_res.to_csv('../tmp/LE.csv', sep=CSV_DELIMITER)

    # Subset results to get requested variables at active sections
    pos_variables = [results.variables['Section'].index(var) for var in VARIABLES]
    pos_sections = [results.emh['Section'].index(section_name) for section_name in bottom.keys()]
    array = res[pos_sections, :][:, pos_variables]

    # Correct some variables (transversal profile)
    # TODO

    # Create output folder if not existing
    out_folder = '../tmp/read_model_and_run'
    if not os.path.exists(out_folder):
        os.makedirs(out_folder)

    # Write a shp file to check
    schema = {
        'geometry': 'Point',
        'properties': {'id_section': 'str'}
    }
    schema['properties'].update({var: 'float' for var in VARIABLES})
    if ADD_BOTTOM:
        schema['properties']['Zf'] = 'float'
    with fiona.open(os.path.join(out_folder, 'debug.shp'), 'w', 'ESRI Shapefile', schema) as out_shp:
        for section_index, (section_name, xyz_array) in enumerate(bottom.items()):
            for x, y, z_bottom in xyz_array:
                values = {}
                for var_index, var in enumerate(VARIABLES):
                    values[var] = array[section_index, var_index]
                layer = {
                    'geometry': mapping(Point(x, y)),
                    'properties': {'id_section': section_name}
                }
                layer['properties'].update(values)
                if ADD_BOTTOM:
                    layer['properties']['Zf'] = z_bottom
                out_shp.write(layer)

except ExceptionCrue10 as e:
    logger.critical(e)
    sys.exit(1)
