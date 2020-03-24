#!/usr/bin/env python
# coding: utf-8
"""
Convertir la géométrie d'un modèle Crue10 au format Mascaret (geo/georef)

TODO: Les transformations suivantes restent à faire :
- Conversion des branches PdC en SaintVenant
- Fusion de branches consécutives
"""
import sys

from crue10.etude import Etude
from crue10.utils.cli_parser import MyArgParse
from crue10.utils import ExceptionCrue10, logger


def crue10_model_geom_to_mascaret(args):
    etude = Etude(args.etu_path)
    modele = etude.get_modele(args.mo_name)
    modele.read_all()
    for sous_modele in modele.liste_sous_modeles:
        sous_modele.remove_sectioninterpolee()
        sous_modele.normalize_geometry()
    modele.write_mascaret_geometry(args.georef_path)


parser = MyArgParse(description=__doc__)
parser.add_argument('etu_path', help="chemin vers l'étude Crue10 à lire (fichier etu.xml)")
parser.add_argument("mo_name", help="nom du modèle (avec le preffixe Mo_)")
parser.add_argument("georef_path", help="chemin vers le fichier de géométrie Mascaret à écrire (extension .georef)")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_model_geom_to_mascaret(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
