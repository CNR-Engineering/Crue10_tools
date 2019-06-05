"""
Lecture de la géométrie (et bathymétrie) d'un sous-modèle Crue10
"""
import sys

from crue10.utils import CrueError, logger
from crue10.emh.section import LitNumerote
from crue10.emh.submodel import SubModel


try:
    submodel = SubModel('../../TatooineMesher_examples/VS2015/in/Etu_VS2015_conc/Etu_VS2003_Conc.etu.xml',
                        'Sm_VS2013_c10_octobre_2014')
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
    # Coordinates of a section
    print(branch.sections[0].get_coord_3d())

    print(submodel.get_section('St_CAF4.000').lits_numerotes)
    print(submodel.get_section('St_CAF5.000').lits_numerotes)
    section = submodel.get_section('St_CAF5.500')
    print(section.lits_numerotes)
    for i_lit, lit_name in enumerate(LitNumerote.LIMITES_NAMES):
        if i_lit == 0:
            point = section.interp_point(section.lits_numerotes[0].xt_min)
        else:
            point = section.interp_point(section.lits_numerotes[i_lit - 1].xt_max)
        print((point.x, point.y))

    submodel.write_shp_limites_lits_numerotes('limites.shp')

except FileNotFoundError as e:
    logger.critical(e)
    sys.exit(1)
except CrueError as e:
    logger.critical(e)
    sys.exit(2)
