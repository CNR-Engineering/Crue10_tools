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
from crue10.study import Study
from crue10.utils import CrueError, logger


ADD_BOTTOM = True
VARIABLES = ['Z', 'H', 'Fr']


etu_folder = '../../TatooineMesher_examples/VS2015/in/Etu_VS2015_conc'
try:
    # Get model
    study = Study(os.path.join(etu_folder, 'Etu_VS2003_Conc.etu.xml'))
    model = study.get_model('Mo_VS2013_c10_octobre_2014')
    model.read_all()
    for submodel in model.submodels:
        submodel.convert_sectionidem_to_sectionprofil()
        print(submodel.summary())

    # Get a dict with active section bottom elevations
    bottom = OrderedDict()
    for section in model.get_section_list():
        if section.is_active and isinstance(section, SectionProfil):
            bottom[section.id] = section.get_coord(add_z=True)

    # Read rcal result file
    scenario = study.get_scenario('Sc_EtatsRef2015')
    run = scenario.get_run('R2019-04-16-14h09m19s')
    results = run.get_results()
    print(results.summary())

    # Check result consistency
    missing_sections = model.get_missing_active_sections(results.emh['Section'])
    if missing_sections:
        print("Missing sections:\n%s" % missing_sections)

    # Read a single *steady* calculation
    res_perm = results.get_res_steady('Cc_360m3-s')
    res = res_perm['Section']

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
        'properties': {'id_section': 'str', **{var: 'float' for var in VARIABLES}}
    }
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
                    'properties': {
                        'id_section': section_name,
                        **values
                    }
                }
                if ADD_BOTTOM:
                    layer['properties']['Zf'] = z_bottom
                out_shp.write(layer)

except CrueError as e:
    logger.critical(e)
    sys.exit(1)
