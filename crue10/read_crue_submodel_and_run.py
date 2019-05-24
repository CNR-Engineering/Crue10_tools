"""

Zf -> from geometry

TODO:
Z -> min(Zf, Z)
H <- Z - Zf
"""
from collections import OrderedDict
import fiona
import numpy as np
import os.path
from shapely.geometry import mapping, Point
import sys

from crue10.run import CrueRun
from crue10.emh.submodel import SubModel
from crue10.utils import CrueError, logger


ADD_BOTTOM = True
VARIABLES = ['Z', 'H', 'Fr']


model_folder = '../../TatooineMesher_examples/VS2015/in/Etu_VS2015_conc'
try:
    # Read submodel
    submodel = SubModel(os.path.join(model_folder, 'Etu_VS2003_Conc.etu.xml'), 'Sm_VS2013_c10_octobre_2014')
    submodel.read_all()
    submodel.convert_sectionidem_to_sectionprofil()

    # Get a dict with active section bottom elevations
    bottom = OrderedDict()
    for _, section in submodel.sections_profil.items():
        if section.is_active:
            bottom[section.id] = section.get_coord_3d()

    # Read rcal result file
    run = CrueRun(os.path.join(model_folder, 'Runs/Sc_EtatsRef2015/R2019-04-16-14h09m19s/Mo_VS2013_c10_octobre_2014',
                  'VS2013_c10_EtatsRef.rcal.xml'))
    print(run.summary())

    # Check result consistency
    missing_sections = submodel.get_missing_active_sections(run.emh['Section'])
    if missing_sections:
        print("Missing sections:\n%s" % missing_sections)

    # Read a single *steady* calculation
    res_perm = run.get_res_perm('Cc_360m3-s')
    res = res_perm['Section']

    # Subset results to get requested variables at active sections
    pos_variables = [run.variables['Section'].index(var) for var in VARIABLES]
    pos_sections = [run.emh['Section'].index(section_name) for section_name in bottom.keys()]
    array = res[pos_sections, :][:, pos_variables]

    # Correct some variables (transversal profile)
    # TODO

    # Write a shp file to check
    schema = {
        'geometry': 'Point',
        'properties': {'id_section': 'str', **{var: 'float' for var in VARIABLES}}
    }
    if ADD_BOTTOM:
        schema['properties']['Zf'] = 'float'
    with fiona.open('debug.shp', 'w', 'ESRI Shapefile', schema) as out_shp:
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

print('END')
