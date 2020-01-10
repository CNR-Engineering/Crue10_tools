#!/usr/bin/env python
# coding: utf-8
"""
Exporter la géométrie d'un modèle Crue10 en shp
"""
import sys

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger
from crue10.utils.cli_parser import MyArgParse


def crue10_model_extract_shp(args):
    etude = Etude(args.etu_path)
    modele = etude.get_modele(args.mo_name)
    modele.read_all()
    print(modele.summary())

    if args.shp_sections:
        modele.write_shp_sectionprofil_as_points(args.shp_sections)

    if args.shp_limits:
        for sous_modele in modele.sous_modeles:
            sous_modele.convert_sectionidem_to_sectionprofil()
        modele.write_shp_limites_lits_numerotes(args.shp_limits)


parser = MyArgParse(description=__doc__)
parser.add_argument('etu_path', help="chemin vers l'étude Crue10 à lire (fichier etu.xml)")
parser.add_argument('mo_name', help="nom du modèle (avec le preffixe Mo_)")

parser_out = parser.add_argument_group("Fichiers de sortie")
parser_out.add_argument('--shp_sections', help="fichier shp avec les sections de type SectionProfil)")
parser_out.add_argument('--shp_limits', help="fichier shp avec les limites de lits numérotées (pour chaque branche)")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_model_extract_shp(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
