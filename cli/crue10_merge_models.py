#!/usr/bin/env python
# coding: utf-8
"""
Ecriture dans un unique modèle Crue10 (dans une étude vierge avec ce modèle) à partir de modèles de différentes études
La liste des suffixes permet de renommer les lois de frottement pour éviter les conflits
TODO: Copy initial conditions!
"""
import argparse
import logging

from crue10.study import Study
from crue10.utils import CrueError, logger


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--etu_path_list', help="liste des chemins vers des fichiers etu.xml", nargs='+')
parser.add_argument('--mo_name_list', help="liste des noms des modèles", nargs='+')
parser.add_argument('--suffix_list', help="liste des suffixes", nargs='+')
parser.add_argument('etu_path_out', help="chemin vers l'étude à écrire")
parser.add_argument('out_name', help="nom des scénario, modèle et sous-modèle (sans le suffixe)")
parser.add_argument('-v', '--verbose', help="increase output verbosity", action="store_true")
args = parser.parse_args()


if args.verbose:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)

try:
    if len(args.etu_path_list) != len(args.mo_name_list) != len(args.suffix_list):
        raise CrueError("Les arguments `etu_path_list`, `suffix_list` et `mo_name_list` n'ont pas la même longueur !")

    study_out = Study(args.etu_path_out, access='w')
    study_out.create_empty_scenario('Sc_%s' % args.out_name, 'Mo_%s' % args.out_name, 'Sm_%s' % args.out_name)
    model_out = study_out.get_model('Mo_%s' % args.out_name)

    for etu_path, mo_name, suffix in zip(args.etu_path_list, args.mo_name_list, args.suffix_list):
        study = Study(etu_path, access='r')
        model = study.get_model(mo_name)
        model.read_all()

        for submodel in model.submodels:
            submodel.rename_emh(suffix)

            study_out.add_submodel(submodel)
            model_out.submodels.append(submodel)

    model_out.reset_initial_conditions()

    logger.info("~> Étude en sortie:")
    logger.info(study_out)
    logger.info(model_out.summary())
    model_out.log_duplicated_emh()

    for _, submodel in study_out.submodels.items():
        logger.info(submodel.summary())

    study_out.write_all()

except CrueError as e:
    logger.error(e)
