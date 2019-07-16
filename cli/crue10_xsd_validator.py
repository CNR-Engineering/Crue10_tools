#!/usr/bin/env python3
"""
Check against XSD validation every crue10 xml files included in the target study (etu.xml file)
"""
import argparse
import logging

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

try:
    study = Study(args.etu_path)
    study.check_xml_files()
except CrueError as e:
    logger.error(e)
