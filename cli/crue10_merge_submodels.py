#!/usr/bin/env python
# coding: utf-8
"""
Fusionner des sous-modèles dans un même sous-modèle
Pour l'instant, seules les lois de frottement sont suffixées
"""
import sys

from crue10.study import Study
from crue10.submodel import SubModel
from crue10.utils import CrueError, logger
from crue10.utils.cli_parser import MyArgParse


def crue10_merge_submodels(args):
    if len(args.etu_path_list) != len(args.sm_name_list) != len(args.suffix_list):
        raise CrueError("Les arguments `etu_path_list`, `suffix_list` et `sm_name_list` n'ont pas la même longueur !")

    first = True
    merged_submodel = None
    for etu_path, sm_name, suffix in zip(args.etu_path_list, args.sm_name_list, args.suffix_list):
        study = Study(etu_path)
        submodel = study.get_submodel(sm_name)
        submodel.read_all()
        print(submodel)

        if first:
            merged_submodel = SubModel(submodel.id, submodel.files)
            first = False
        merged_submodel.add_emh_from_submodel(submodel, suffix)

    print("~> Merged submodel:")
    print(merged_submodel)
    merged_submodel.write_all(args.output_folder)


parser = MyArgParse(description=__doc__)
parser.add_argument('--etu_path_list', help="liste des chemins vers des fichiers etu.xml", nargs='+')
parser.add_argument('--sm_name_list', help="liste des noms des sous-modèles", nargs='+')
parser.add_argument('--suffix_list', help="liste des sufixes", nargs='+')
parser.add_argument('output_folder', help="nom du dossier de sortie")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_merge_submodels(args)
    except CrueError as e:
        logger.critical(e)
        sys.exit(1)
