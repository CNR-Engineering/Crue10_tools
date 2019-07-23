#!/usr/bin/env python3
"""
Check against XSD validation every crue10 xml files included in the target study (etu.xml file)
"""
import argparse
import logging
import sys

from crue10.study import Study
from crue10.utils import CrueError, logger


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('etu_path', help="path to etu.xml file")
parser.add_argument('-v', '--verbose', help="increase output verbosity", action="store_true")
args = parser.parse_args()

if args.verbose:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

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
    sys.exit(1)
else:
    logger.info("Aucune erreur détectée dans les fichiers XML.")
    sys.exit(0)
