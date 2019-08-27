#!/usr/bin/env python
# coding: utf-8
"""
Check against XSD validation every crue10 xml files
included in the target study (etu.xml file)
"""
import sys

from crue10.study import Study
from crue10.utils import CrueError, logger
from crue10.utils.cli_parser import MyArgParse


def crue10_xsd_validator(args):
    has_error = False
    study = Study(args.etu_path)
    errors = study.check_xml_files()

    for file, errors in errors.items():
        if errors:
            has_error = True
            logger.error("~> Fichier %s" % file)
            for error_msg in errors:
                logger.error(error_msg)

    if has_error:
        logger.critical("Des erreurs ont été trouvés dans les fichiers XML.")
        sys.exit(2)
    else:
        logger.info("Aucune erreur détectée dans les fichiers XML.")
        sys.exit(0)


parser = MyArgParse(description=__doc__)
parser.add_argument('etu_path', help="chemin vers l'étude Crue10 à lire (fichier etu.xml)")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_xsd_validator(args)
    except CrueError as e:
        logger.critical(e)
        sys.exit(1)
