"""
Lecture de la géométrie (et bathymétrie) d'un sous-modèle Crue10
"""
import sys

from crue10.utils import CrueError, logger
from crue10.emh.submodel import SubModel


try:
    submodel = SubModel('../../tatooinemesher_examples/VS2015/in/Etu_VS2015_conc/Etu_VS2003_Conc.etu.xml',
                        'Sm_VS2013_c10_octobre_2014')
    submodel.read_all()

    # Do something with `submodel`...
    print(submodel)
    # submodel.remove_sectioninterpolee()
    # submodel.convert_sectionidem_to_sectionprofil()

except FileNotFoundError as e:
    logger.critical(e)
    sys.exit(1)
except CrueError as e:
    logger.critical(e)
    sys.exit(2)
