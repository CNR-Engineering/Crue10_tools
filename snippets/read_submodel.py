# coding: utf-8
"""
Lecture d'un sous-modèle Crue10
"""
import os.path
import sys

from crue10.utils import CrueError, logger
from crue10.emh.section import LitNumerote
from crue10.study import Study


try:
    # Get submodel
    study = Study(os.path.join('..', '..', 'Crue10_examples', 'Etudes-tests',
                               'Etu_BE2016_conc', 'Etu_BE2016_conc.etu.xml'))
    submodel = study.get_submodel('Sm_BE2016_etatref')
    submodel.read_all()

    # Do something with `submodel`...
    # Here is an example below:
    submodel.remove_sectioninterpolee()
    submodel.convert_sectionidem_to_sectionprofil()

    # Select a single branch
    branch = submodel.get_branche('Br_VRH99.900')
    print(branch)
    # Sections of a single branch
    print(branch.sections)
    # Select a section (the first in this case) with its index within the branch
    section = branch.sections[0]
    print(section)
    print(section.get_coord(add_z=True))  # 3D coordinates
    # Select another section by its identifier
    section = submodel.get_section('St_KBE09_BE10_am')
    # Display coordinates of its limits
    print(section.lits_numerotes)
    for i_lit, lit_name in enumerate(LitNumerote.LIMIT_NAMES):
        if i_lit == 0:
            point = section.interp_point(section.lits_numerotes[0].xt_min)
        else:
            point = section.interp_point(section.lits_numerotes[i_lit - 1].xt_max)
        print((point.x, point.y))

except FileNotFoundError as e:
    logger.critical(e)
    sys.exit(1)
except CrueError as e:
    logger.critical(e)
    sys.exit(2)
