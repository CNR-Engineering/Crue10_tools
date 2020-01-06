# coding: utf-8
import logging
import numpy as np
import os.path
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
submodel.add_default_friction_laws()

# Add nodes
noeud1 = Noeud('Nd_1')
noeud1.set_geom(Point(0, 100))
submodel.add_noeud(noeud1)

noeud2 = Noeud('Nd_2')
noeud2.set_geom(Point(0, 90))
submodel.add_noeud(noeud2)

noeud4 = Noeud('Nd_4')
noeud4.set_geom(Point(0, 70))
submodel.add_noeud(noeud4)

noeud5 = Noeud('Nd_5')
noeud5.set_geom(Point(0, 60))
submodel.add_noeud(noeud5)

noeud6 = Noeud('Nd_6')
noeud6.set_geom(Point(0, 50))
submodel.add_noeud(noeud6)

noeud12 = Noeud('Nd_12')
noeud12.set_geom(Point(0, -10))
submodel.add_noeud(noeud12)

noeud14 = Noeud('Nd_14')
noeud14.set_geom(Point(0, -30))
submodel.add_noeud(noeud14)

noeud15 = Noeud('Nd_15')
noeud15.set_geom(Point(0, -40))
submodel.add_noeud(noeud15)

noeud20 = Noeud('Nd_20')
noeud20.set_geom(Point(0, -90))
submodel.add_noeud(noeud20)

noeud_aval = Noeud('Nd_aval')
noeud_aval.set_geom(Point(0, -150))
submodel.add_noeud(noeud_aval)


# Add a casier
casier = Casier('Ca_1', noeud1)
casier.add_profil_casier(ProfilCasier('Pc_' + casier.id[3:] + '_001'))
casier.set_geom(LinearRing([(-4, 96), (4, 96), (4, 104), (-4, 104)]))
submodel.add_casier(casier)


# Define an hydraulic axis line, used only to compute orthogonal trace (for SectionProfil)
axe_geom = LineString([(noeud1.geom.x, noeud1.geom.x), (noeud_aval.geom.x, noeud_aval.geom.y)])


# Add sections
section1_am = SectionSansGeometrie('St_1_Am')
submodel.add_section(section1_am)
section1_av = SectionSansGeometrie('St_1_Av')
submodel.add_section(section1_av)

section2_am = SectionProfil('St_2_Am')
section2_am.set_xz(np.array([(0, 3), (1, 0.5), (5, 0), (9, 0.5), (10, 3)]))
section2_am.add_limite_geom(LimiteGeom('Et_AxeHyd', 5.0))
section2_am.set_lits_numerotes((0.0, 0.0, 1.0, 9.0, 10.0, 10.0))
section2_am.build_orthogonal_trace(axe_geom)
submodel.add_section(section2_am)

section2_av = SectionIdem('St_2_Av', section2_am, dz=0.0)
submodel.add_section(section2_av)

section4_am = SectionSansGeometrie('St_4_Am')
submodel.add_section(section4_am)
section4_av = SectionSansGeometrie('St_4_Av')
submodel.add_section(section4_av)

section5_am = SectionSansGeometrie('St_5_Am')
submodel.add_section(section5_am)
section5_av = SectionSansGeometrie('St_5_Av')
submodel.add_section(section5_av)

section6_am = SectionIdem('St_6_Am', section2_am, dz=0.0)
submodel.add_section(section6_am)
section6_av = SectionIdem('St_6_Av', section2_am, dz=0.0)
submodel.add_section(section6_av)

section12_am = SectionSansGeometrie('St_12_Am')
submodel.add_section(section12_am)
section12_av = SectionSansGeometrie('St_12_Av')
submodel.add_section(section12_av)

section14_am = SectionSansGeometrie('St_14_Am')
submodel.add_section(section14_am)
section14_av = SectionSansGeometrie('St_14_Av')
submodel.add_section(section14_av)

section15_am = SectionIdem('St_15_Am', section2_am, dz=0.0)
submodel.add_section(section15_am)
section15_av = SectionIdem('St_15_Av', section2_am, dz=0.0)
submodel.add_section(section15_av)

section20_am = SectionIdem('St_20_Am', section2_am, dz=0.0)
submodel.add_section(section20_am)

section20_middle = SectionProfil('St_20_middle')
section20_middle.set_xz(np.array([(0, 3), (1, 0.5), (5, 0), (9, 0.5), (10, 3)]))
section20_middle.set_fente(0.15, 15)
section20_middle.add_limite_geom(LimiteGeom('Et_AxeHyd', 5.0))
section20_middle.set_lits_numerotes((0.0, 0.0, 1.0, 9.0, 10.0, 10.0))
section20_middle.build_orthogonal_trace(axe_geom)
submodel.add_section(section20_middle)

section20_av = SectionIdem('St_20_Av', section20_middle, dz=-1.0)
submodel.add_section(section20_av)


# Add branches
branche1 = BranchePdC('Br_1-PdC', noeud1, noeud2)
# branche1.set_geom(LineString([(0, 100), (0, 90)]))  # this is already the default behaviour
branche1.add_section(section1_am, 0.0)
branche1.add_section(section1_av, 11.0)  # => branche1.length = 11 m
submodel.add_branche(branche1)

branche2 = BrancheSeuilTransversal('Br_2-SeuilTransversal', noeud2, noeud4)
branche2.add_section(section2_am, 0.0)
branche2.add_section(section2_av, 10.1)
submodel.add_branche(branche2)

branche4 = BrancheSeuilLateral('Br_4-SeuilLateral', noeud4, noeud5)
branche4.add_section(section4_am, 0.0)
branche4.add_section(section4_av, 9.9)
submodel.add_branche(branche4)

branche5 = BrancheOrifice('Br_5-Orifice', noeud5, noeud6)
branche5.add_section(section5_am, 0.0)
branche5.add_section(section5_av, 9.9)
submodel.add_branche(branche5)

branche6 = BrancheStrickler('Br_6-Strickler', noeud6, noeud12)
branche6.add_section(section6_am, 0.0)
branche6.add_section(section6_av, 10.0)
submodel.add_branche(branche6)

branche12 = BrancheNiveauxAssocies('Br_12-NiveauxAssocies', noeud12, noeud14)
branche12.add_section(section12_am, 0.0)
branche12.add_section(section12_av, 10.0)
submodel.add_branche(branche12)

branche14 = BrancheBarrageGenerique('Br_14-BarrageGenerique', noeud14, noeud15)
branche14.section_pilotage = section1_am
branche14.add_section(section14_am, 0.0)
branche14.add_section(section14_av, 10.0)
submodel.add_branche(branche14)

branche15 = BrancheBarrageFilEau('Br_15-BarrageFilEau', noeud15, noeud20)
branche15.section_pilotage = section1_am
branche15.add_section(section15_am, 0.0)
branche15.add_section(section15_av, 10.0)
submodel.add_branche(branche15)

branche20 = BrancheSaintVenant('Br_20-SaintVenant', noeud20, noeud_aval)
branche20.add_section(section20_am, 0.0)
branche20.add_section(section20_middle, 25.0)
branche20.add_section(section20_av, 50.0)
submodel.add_branche(branche20)


if __name__ == "__main__":
    # Write all submodel files
    submodel.write_all(os.path.join('out', 'Sm_from_scratch'), 'Config')
