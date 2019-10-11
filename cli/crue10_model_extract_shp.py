#!/usr/bin/env python
# coding: utf-8
"""
Exporter la géométrie d'un modèle Crue10 en shp
"""
import sys

from crue10.study import Study
from crue10.utils import CrueError, logger
from crue10.utils.cli_parser import MyArgParse


def crue10_model_extract_shp(args):
    study = Study(args.etu_path)
    model = study.get_model(args.mo_name)
    model.read_all()
    print(model.summary())

    if args.shp_sections:
        model.write_shp_sectionprofil_as_points(args.shp_sections)

    if args.shp_limits:
        for submodel in model.submodels:
            submodel.convert_sectionidem_to_sectionprofil()
        model.write_shp_limites_lits_numerotes(args.shp_limits)


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
    except CrueError as e:
        logger.critical(e)
        sys.exit(1)
