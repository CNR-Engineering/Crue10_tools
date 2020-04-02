# coding: utf-8
"""
Lecture d'un sous-modèle Crue10
"""
import os.path
import sys

from crue10.utils import ExceptionCrue10, logger
from crue10.emh.section import LitNumerote
from crue10.sous_modele import SousModele
from crue10.etude import Etude


try:
    dossier = os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc', 'Etu_BE2016_conc')
    nom_sous_modele = 'Sm_BE2016_etatref'

    # Get sous_modele from a study
    etude = Etude(os.path.join(dossier, 'Etu_BE2016_conc.etu.xml'))
    etude.read_all()
    sous_modele = etude.get_sous_modele(nom_sous_modele)

    # # Get sous_modele directly from a dict containing path to xml/shp files
    # files = {xml: os.path.join(dossier, nom_sous_modele[3:] + '.' + xml + '.xml')
    #          for xml in SousModele.FILES_XML}
    # for shp_name in SousModele.FILES_SHP:
    #     files[shp_name] = os.path.join(dossier, 'Config', nom_sous_modele.upper(), shp_name + '.shp')
    # sous_modele = SousModele(nom_sous_modele, access='r', files=files, metadata=None)
    # sous_modele.read_all()

    # Do something with `sous_modele`...
    # Here is an example below:
    sous_modele.remove_sectioninterpolee()  #FIXME: some IC/BC can become inconsistent
    sous_modele.convert_sectionidem_to_sectionprofil()

    # Select a single branch
    branch = sous_modele.get_branche('Br_VRH99.900')
    print(branch)
    # Sections of a single branch
    print(branch.liste_sections_dans_branche)
    # Select a section (the first in this case) with its index within the branch
    section = branch.liste_sections_dans_branche[0]
    print(section)
    print(section.get_coord(add_z=True))  # 3D coordinates
    # Select another section by its identifier
    section = sous_modele.get_section('St_KBE09_BE10_am')
    # Display coordinates of its limits
    print(section.lits_numerotes)
    for i_lit, lit_name in enumerate(LitNumerote.LIMIT_NAMES):
        if i_lit == 0:
            point = section.interp_point(section.lits_numerotes[0].xt_min)
        else:
            point = section.interp_point(section.lits_numerotes[i_lit - 1].xt_max)
        print((point.x, point.y))

    # Check reloading of a modified study
    etude.write_all('out')
    new_etude = Etude(os.path.join('out', os.path.basename(etude.etu_path)))
    new_etude.check_xml_files()
    new_etude.read_all()

except IOError as e:
    logger.critical(e)
    sys.exit(1)
except ExceptionCrue10 as e:
    logger.critical(e)
    sys.exit(2)
