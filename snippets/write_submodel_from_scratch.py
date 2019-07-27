import logging
import numpy as np
from shapely.geometry import Point, LinearRing, LineString

from crue10.emh.branche import *
from crue10.emh.casier import Casier, ProfilCasier
from crue10.emh.noeud import Noeud
from crue10.emh.section import *
from crue10.submodel import SubModel
from crue10.utils import logger

logger.setLevel(logging.DEBUG)


# Build a submodel
submodel = SubModel('Sm_fromscratch', access='w')

# Create default friction laws
submodel.add_default_friction_laws()
fk_sto = submodel.friction_laws['FkSto_K0_0001']
fk_min = submodel.friction_laws['Fk_DefautMaj']
fk_maj = submodel.friction_laws['Fk_DefautMin']

noeud1 = Noeud('Nd_RET1.000')
noeud1.set_geom(Point(0, 0))
submodel.add_noeud(noeud1)

noeud2 = Noeud('Nd_RET10.000')
noeud2.set_geom(Point(1000, 1000))
submodel.add_noeud(noeud2)


# Create a Casier with its associated casier
noeud3 = Noeud('Nd_PLAINE1')
noeud3.set_geom(Point(0, 1000))
submodel.add_noeud(noeud3)

casier = Casier('Ca_PLAINE1', noeud3)
casier.add_profil_casier(ProfilCasier('Pc_' + casier.id[3:] + '_001'))
casier.set_geom(LinearRing([(-250, 750), (250, 750), (250, 1250), (-250, 1250)]))
submodel.add_casier(casier)


# Define a BrancheSeuilLateral with its 2 SectionSansGeometrie
section1 = SectionSansGeometrie('St_RET1.000-PLAINE1')
submodel.add_section(section1)

section2 = SectionSansGeometrie('St_PLAINE1')
submodel.add_section(section2)

line = LineString([(0, 0), (0, 1000)])
branche1 = BrancheSeuilLateral('Br_RET1.000-PLAINE1', noeud1, noeud3)
branche1.set_geom(line)
branche1.add_section(section1, 0.0)
branche1.add_section(section1, 950.0)  # => branche1.length = 950 m


# Define a BrancheSaintVenant with its 2 sections (1 SectionProfil + 1 SectionIdem)
line = LineString([(0, 0), (450, 550), (1000, 1000)])

section3 = SectionProfil('St_RET1.000')
section3.set_xz(np.array([(0, 3), (10, 0.5), (50, 0), (90, 0.5), (100, 3)]))
section3.add_limite_geom(LimiteGeom('Et_AxeHyd', 50.0))
section3.add_lit_numerote(LitNumerote('Lt_StoD', 0.0, 0.0))
section3.add_lit_numerote(LitNumerote('Lt_MajD', 0.0, 10.0))
section3.add_lit_numerote(LitNumerote('Lt_Mineur', 10.0, 90.0))
section3.add_lit_numerote(LitNumerote('Lt_MajG', 90.0, 100.0))
section3.add_lit_numerote(LitNumerote('Lt_StoG', 100.0, 100.0))
section3.build_orthogonal_trace(line)
submodel.add_section(section3)

section4 = SectionIdem('St_RET1.000a', section3, dz=0.0)
submodel.add_section(section4)

branche2 = BrancheSaintVenant('Br_RET1.000', noeud1, noeud2)
branche2.set_geom(line)
branche2.add_section(section3, 0.0)
branche2.add_section(section4, 1100.0)  # => branche2.length = 1100 m
submodel.add_branche(branche2)


if __name__ == "__main__":
    # Write all submodel files
    submodel.write_all('../tmp/Sm_from_scratch', 'Config')
