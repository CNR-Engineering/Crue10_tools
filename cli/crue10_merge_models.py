#!/usr/bin/env python
# coding: utf-8
"""
Regrouper les sous-modèles de plusieurs modèles (issus d'études différentes)
dans une étude ne contenant qu'un seul scénario avec un seul modèle.

Dans l'étude en sortie, les conditions initiales sont conservées,
mais tous les autres paramètres/données des modèles sont ignorés ou remis
à leur valeur par défaut (conditions aux limites, paramètres de calculs...).

L'argument `suffix_list` permet de renommer les EMHs et les lois de frottement
pour éviter les conflits.

Les arguments `--etu_path_list`, `--suffix_list` et `--mo_name_list`
doivent avoir la même longueur.
"""
import sys

from crue10.study import Study
from crue10.utils import CrueError, logger
from crue10.utils.cli_parser import MyArgParse


def crue10_merge_models(args):
    if len(args.etu_path_list) != len(args.mo_name_list) != len(args.suffix_list):
        raise CrueError("Les arguments `--etu_path_list`, `--suffix_list` et `--mo_name_list`"
                        " n'ont pas la même longueur !")

    # Parse argument `--nodes_to_merge`
    nb_models = len(args.mo_name_list)
    noeud_id_list = [[] for _ in range(nb_models)]
    if args.nodes_to_merge is not None:
        for nodes_str in args.nodes_to_merge:
            nodes = nodes_str.split(',')
            if len(nodes) != nb_models:
                raise CrueError("L'argument `--nodes_to_merge ` doit être composé de groupe(s) de %i noeuds"
                                % nb_models)
            for i, node_id in enumerate(nodes):
                noeud_id_list[i].append(node_id)

    study_out = Study(args.etu_path_out, access='w')
    study_out.create_empty_scenario('Sc_%s' % args.out_name, 'Mo_%s' % args.out_name, submodel_name=None)
    model_out = study_out.get_model('Mo_%s' % args.out_name)

    for i, (etu_path, mo_name, suffix) in enumerate(zip(args.etu_path_list, args.mo_name_list, args.suffix_list)):
        study_in = Study(etu_path, access='r')
        model_in = study_in.get_model(mo_name)
        model_in.read_all()

        model_in.rename_emhs(suffix, emhs_to_preserve=noeud_id_list[i])
        for j, noeud_id in enumerate(noeud_id_list[i]):
            if noeud_id not in [nd.id for nd in model_in.get_noeud_list()]:
                raise CrueError("Le noeud %s n'est pas dans le modèle %s" % (noeud_id, model_in.id))
            model_in.rename_noeud(noeud_id, noeud_id_list[0][j])

        model_out.append_from_model(model_in)

    logger.info("~> Étude en sortie:")
    logger.info(study_out)
    logger.info(model_out.summary())
    model_out.log_duplicated_emh()

    for submodel in model_out.submodels:
        study_out.add_submodel(submodel)
        logger.info(submodel.summary())

    study_out.write_all()


parser = MyArgParse(description=__doc__)
parser.add_argument('--etu_path_list', help="liste des chemins vers les fichiers etu.xml", nargs='+', default=[])
parser.add_argument('--mo_name_list', help="liste des noms les modèles", nargs='+', default=[])
parser.add_argument('--suffix_list', help="liste des suffixes à ajouter", nargs='+', default=[])
parser.add_argument('--nodes_to_merge', help="liste des noeuds à fusionner", nargs='*', default=[])
parser.add_argument('etu_path_out', help="chemin vers l'étude à écrire")
parser.add_argument('out_name', help="nom générique pour les scénario, modèle et sous-modèle (sans le suffixe)")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_merge_models(args)
    except CrueError as e:
        logger.critical(e)
        sys.exit(1)
