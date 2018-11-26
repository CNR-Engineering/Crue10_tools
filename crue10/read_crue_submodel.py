"""
Lecture de la géométrie (et bathymétrie) d'un sous-modèle Crue10

Branches: seules les branches avec les sections profil ou idem sont traitées
- EMHBrancheSaintVenant (type 20)
- EMHBrancheSeuilTransversal (type 4) => TODO
- EMHBrancheStrickler (type 6) => TODO
(- EMHBrancheBarrageFil est ignoré (type 15))
/!\ Les branches sont orientées

Particularités :
- SectionIdem: la traceProfil est regénérée => TODO
"""
import sys

from crue10.utils import CrueError, logger
from crue10.emh.submodel import SubModel


try:
    model = SubModel('../../crue10_examples/Etu_VS2015_conc/Etu_VS2003_Conc.etu.xml',
                     'Sm_VS2013_c10_octobre_2014')
    model.read_drso()
    model.read_dptg()
    model.read_shp_traces_sections()
    model.read_shp_branches()

    # Do something with `model`...
    print(model)

except FileNotFoundError as e:
    logger.critical(e)
    sys.exit(1)
except CrueError as e:
    logger.critical(e)
    sys.exit(2)
