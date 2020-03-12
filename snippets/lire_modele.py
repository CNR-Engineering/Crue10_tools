# coding: utf-8
"""
Lecture d'un modèle Crue10
"""
import os.path
import sys

from crue10.utils import ExceptionCrue10, logger
from crue10.etude import Etude


try:
    FileNotFoundError
except NameError:  # Python2 fix
    FileNotFoundError = IOError

try:
    # Get modele
    etude = Etude(os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc',
                               'Etu_BE2016_conc', 'Etu_BE2016_conc.etu.xml'))
    modele = etude.get_scenario_courant().modele
    modele.read_all()

    print(modele)
    for sous_modele in modele.liste_sous_modeles:
        print(sous_modele)
        # sous_modele.convert_sectionidem_to_sectionprofil()

    # Write some output files
    # modele.write_mascaret_geometry('../tmp/Etu_VS2003_Conc.georef')
    modele.write_shp_limites_lits_numerotes('../tmp/limites.shp')
    modele.write_shp_sectionprofil_as_points('../tmp/liste_sections.shp')

except FileNotFoundError as e:
    logger.critical(e)
    sys.exit(1)
except ExceptionCrue10 as e:
    logger.critical(e)
    sys.exit(2)
