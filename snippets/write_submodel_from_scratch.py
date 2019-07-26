import logging
from shapely.geometry import Point, LinearRing, LineString

from crue10.emh.branche import BrancheSaintVenant
from crue10.emh.casier import Casier
from crue10.emh.noeud import Noeud
from crue10.submodel import SubModel
from crue10.utils import logger

logger.setLevel(logging.DEBUG)


# Build a submodel
submodel = SubModel('Sm_fromscratch', access='w')

noeud1 = Noeud('Nd_RET1.000')
noeud1.set_geom(Point(0, 0))
submodel.add_noeud(noeud1)

noeud2 = Noeud('Nd_RET10.000')
noeud2.set_geom(Point(10, 10))
submodel.add_noeud(noeud2)

branche = BrancheSaintVenant('Br_RET1.000', noeud1, noeud2)
branche.set_geom(LineString([(0, 0), (10, 10)]))
submodel.add_branche(branche)

noeud3 = Noeud('Nd_PLAINE1')
noeud3.set_geom(Point(0, 10))
submodel.add_noeud(noeud3)

casier = Casier('Cd_PLAINE1', noeud3.id)
casier.set_geom(LinearRing([(0, 7), (3, 10), (0, 10)]))
submodel.add_casier(casier)


# Write all submodel files
submodel.write_all('../tmp/Sm_from_scratch')
