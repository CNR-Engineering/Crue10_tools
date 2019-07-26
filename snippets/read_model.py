"""
Lecture d'un modèle Crue10
"""
import sys

from crue10.utils import CrueError, logger
from crue10.study import Study


try:
    # Get model
    study = Study('../../TatooineMesher_examples/VS2015/in/Etu_VS2015_conc/Etu_VS2003_Conc.etu.xml')
    model = study.get_model('Mo_VS2013_c10_octobre_2014')
    model.read_all()

    print(model)
    for submodel in model.submodels:
        print(submodel)

except FileNotFoundError as e:
    logger.critical(e)
    sys.exit(1)
except CrueError as e:
    logger.critical(e)
    sys.exit(2)
