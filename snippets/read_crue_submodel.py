"""
Lecture de la géométrie (et de la bathymétrie) d'un sous-modèle Crue10
"""
import sys

from crue10.utils import CrueError, logger
from crue10.emh.section import LitNumerote
from crue10.study import Study


try:
    # Get submodel
    study = Study('../../TatooineMesher_examples/VS2015/in/Etu_VS2015_conc/Etu_VS2003_Conc.etu.xml')
    submodel = study.get_submodel('Sm_VS2013_c10_octobre_2014')
    submodel.read_all()

    # Do something with `submodel`...
    # Here is an example below:
    submodel.remove_sectioninterpolee()
    submodel.convert_sectionidem_to_sectionprofil()

    # Select a single branch
    branch = submodel.branches['Br_AVB5.560']
    print(branch)
    # Sections of a single branch
    print(branch.sections)
    # Select a section (the first in this case) with its index within the branch
    section = branch.sections[0]
    print(section)
    print(section.get_coord(add_z=True))  # 3D coordinates
    # Select another section by its identifier
    section = submodel.sections['St_CAF5.500']
    # Display coordinates of its limits
    print(section.lits_numerotes)
    for i_lit, lit_name in enumerate(LitNumerote.LIMIT_NAMES):
        if i_lit == 0:
            point = section.interp_point(section.lits_numerotes[0].xt_min)
        else:
            point = section.interp_point(section.lits_numerotes[i_lit - 1].xt_max)
        print((point.x, point.y))

    # Write some output files
    submodel.write_shp_limites_lits_numerotes('limites.shp')
    submodel.convert_to_mascaret_format('Etu_VS2003_Conc.georef')

except FileNotFoundError as e:
    logger.critical(e)
    sys.exit(1)
except CrueError as e:
    logger.critical(e)
    sys.exit(2)
