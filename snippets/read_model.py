# coding: utf-8
"""
Lecture d'un modèle Crue10
"""
import os.path
import sys

from crue10.utils import CrueError, logger
from crue10.study import Study


try:
    FileNotFoundError
except NameError:  # Python2 fix
    FileNotFoundError = IOError

try:
    # Get model
    study = Study(os.path.join('..', '..', 'Crue10_examples', 'Etudes-tests',
                               'Etu_BE2016_conc', 'Etu_BE2016_conc.etu.xml'))
    model = study.get_model('Mo_BE2016_etatref')
    model.read_all()

    print(model)
    for submodel in model.submodels:
        print(submodel)
        # submodel.convert_sectionidem_to_sectionprofil()

    # Write some output files
    # model.write_mascaret_geometry('../tmp/Etu_VS2003_Conc.georef')
    model.write_shp_limites_lits_numerotes('../tmp/limites.shp')
    model.write_shp_sectionprofil_as_points('../tmp/sections.shp')

except FileNotFoundError as e:
    logger.critical(e)
    sys.exit(1)
except CrueError as e:
    logger.critical(e)
    sys.exit(2)
