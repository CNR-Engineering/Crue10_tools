#!/usr/bin/env python
# coding: utf-8
"""
Fusionner des sous-modèles dans un même sous-modèle
Pour l'instant, seules les lois de frottement sont suffixées
"""
import sys

from crue10.etude import Etude
from crue10.sous_modele import SousModele
from crue10.utils import ExceptionCrue10, logger
from crue10.utils.cli_parser import MyArgParse


def crue10_merge_sous_modeles(args):
    if len(args.etu_path_list) != len(args.sm_name_list) != len(args.suffix_list):
        raise ExceptionCrue10("Les arguments `etu_path_list`, `suffix_list` et `sm_name_list` n'ont pas la même longueur !")

    first = True
    merged_sous_modele = None
    for etu_path, sm_name, suffix in zip(args.etu_path_list, args.sm_name_list, args.suffix_list):
        study = Etude(etu_path)
        sous_modele = study.get_sous_modele(sm_name)
        sous_modele.read_all()
        print(sous_modele)

        if first:
            merged_sous_modele = SousModele(sous_modele.id, sous_modele.files)
            first = False
        merged_sous_modele.ajouter_emh_depuis_sous_modele(sous_modele, suffix)

    print("~> Merged sous_modele:")
    print(merged_sous_modele)
    merged_sous_modele.write_all(args.output_folder)


parser = MyArgParse(description=__doc__)
parser.add_argument('--etu_path_list', help="liste des chemins vers des fichiers etu.xml", nargs='+')
parser.add_argument('--sm_name_list', help="liste des noms des sous-modèles", nargs='+')
parser.add_argument('--suffix_list', help="liste des sufixes", nargs='+')
parser.add_argument('output_folder', help="nom du dossier de sortie")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_merge_sous_modeles(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
