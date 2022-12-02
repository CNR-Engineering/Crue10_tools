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
        raise ExceptionCrue10("Les arguments `etu_path_list`, `suffix_list` "
                              "et `sm_name_list` n'ont pas la même longueur !")
    if len(args.etu_path_list) < 2:
        raise ExceptionCrue10("Il faut au moins 2 sous-modèles pour faire la fusion !")

    merged_sous_modele = None
    for etu_path, sm_name, suffix in zip(args.etu_path_list, args.sm_name_list, args.suffix_list):
        etude = Etude(etu_path)
        sous_modele = etude.get_sous_modele(sm_name)
        sous_modele.read_all()
        logger.info(sous_modele)

        if merged_sous_modele is None:
            merged_sous_modele = SousModele(sous_modele.id, files=sous_modele.files,
                                            version_grammaire=sous_modele.version_grammaire)
        merged_sous_modele.ajouter_emh_depuis_sous_modele(sous_modele, suffix)

    logger.info("~> Sous-modèle fusionné:")
    logger.info(merged_sous_modele)
    merged_sous_modele.write_all(args.output_folder, folder_config='Config')


parser = MyArgParse(description=__doc__)
parser_submodels = parser.add_argument_group("Choix des sous-modèles à fusionner")
parser_submodels.add_argument('--etu_path_list', help="liste des chemins vers des fichiers etu.xml", nargs='+',
                              required=True)
parser_submodels.add_argument('--sm_name_list', help="liste des noms des sous-modèles", nargs='+', required=True)
parser_submodels.add_argument('--suffix_list', help="liste des suffixes", nargs='+', required=True)
parser.add_argument('output_folder', help="nom du dossier de sortie")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_merge_sous_modeles(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
