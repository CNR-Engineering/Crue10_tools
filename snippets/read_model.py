"""
Lecture d'un modèle Crue10
"""
import sys

from crue10.utils import CrueError, logger
from crue10.study import Study


try:
    # Get model
    study = Study('../crue10_examples/Etudes-tests/Etu_BE2016_conc/Etu_BE2016_conc.etu.xml')
    model = study.get_model('Mo_BE2016_etatref')
    model.read_all()

    print(model)
    for submodel in model.submodels:
        print(submodel)

    # model.write_mascaret_geometry('../tmp/Etu_VS2003_Conc.georef')

except FileNotFoundError as e:
    logger.critical(e)
    sys.exit(1)
except CrueError as e:
    logger.critical(e)
    sys.exit(2)
