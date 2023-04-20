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

L'argument `--nodes_to_share` permet de définir les noeuds communs,
qui seront renommés pour correspondre au premier noeud. Les groupes de noeuds sont
séparés par des espaces et au sein de ceux-ci les noeuds sont séparés par des virgules.
Les valeurs vides sont permises si le sous-modèle n'est pas concerné.
"""
import sys

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger
from crue10.utils.cli_parser import MyArgParse


def crue10_merge_models(args):
    if len(args.etu_path_list) != len(args.mo_name_list) != len(args.suffix_list):
        raise ExceptionCrue10("Les arguments `--etu_path_list`, `--suffix_list` et `--mo_name_list`"
                              " n'ont pas la même longueur !")
    if len(args.etu_path_list) < 2:
        raise ExceptionCrue10('Il faut mentionner au moins les deux modèles à fusionner')

    # Parse argument `--nodes_to_share`
    nb_models = len(args.mo_name_list)
    noeud_id_list = [[] for _ in range(nb_models)]
    noeud_id_references = []  # list of node name used for merged nodes (first node found)
    if args.nodes_to_share is not None:
        for nodes_str in args.nodes_to_share:
            nodes = nodes_str.split(',')
            if len(nodes) != nb_models:
                raise ExceptionCrue10("L'argument `--nodes_to_share` doit être composé de groupe(s) de %i noeuds"
                                      % nb_models)
            reference_found = False
            for i, node_id in enumerate(nodes):
                noeud_id_list[i].append(node_id)
                if not reference_found and node_id != '':
                    noeud_id_references.append(node_id)
                    reference_found = True
            if not reference_found:
                raise ExceptionCrue10("Le noeud de référence n'a pas pu être trouvé pour : `%s`" % nodes_str)

    study_first = Etude(args.etu_path_list[0], mode='r')
    study_out = Etude(args.etu_path_out, mode='w', version_grammaire=study_first.version_grammaire)
    study_out.create_empty_scenario('Sc_%s' % args.out_name, 'Mo_%s' % args.out_name, nom_sous_modele=None)
    model_out = study_out.get_modele('Mo_%s' % args.out_name)

    for i, (etu_path, mo_name, suffix) in enumerate(zip(args.etu_path_list, args.mo_name_list, args.suffix_list)):
        study_in = Etude(etu_path, mode='r')
        model_in = study_in.get_modele(mo_name)
        model_in.read_all()

        # Rename all EMHs and set optional shared nodes
        model_in.rename_emhs(suffix, emhs_to_preserve=noeud_id_list[i])
        for j, noeud_id in enumerate(noeud_id_list[i]):
            if noeud_id != '':
                if noeud_id not in [nd.id for nd in model_in.get_liste_noeuds()]:
                    raise ExceptionCrue10("Le noeud %s n'est pas dans le modèle %s" % (noeud_id, model_in.id))
                model_in.rename_noeud(noeud_id, noeud_id_references[j])

        model_out.ajouter_depuis_modele(model_in)

    logger.info("~> Étude en sortie:")
    logger.info(study_out)
    logger.info(model_out.summary())
    model_out.log_duplicated_emh()

    for sous_modele in model_out.liste_sous_modeles:
        study_out.ajouter_sous_modele(sous_modele)
        logger.info(sous_modele.summary())

    study_out.write_all()


parser = MyArgParse(description=__doc__)
parser_models = parser.add_argument_group("Choix des modèles à fusionner")
parser_models.add_argument('--etu_path_list', nargs='+', default=[],
                           help="liste des chemins vers les études Crue10 à lire (fichiers etu.xml)")
parser_models.add_argument('--mo_name_list', nargs='+', default=[],
                           help="liste des noms des modèles (avec le preffixe Mo_)")
parser_models.add_argument('--suffix_list', help="liste des suffixes à ajouter aux EMHs", nargs='+', default=[])

parser.add_argument('--nodes_to_share', nargs='*', default=[],
                    help="liste des noeuds à fusionner (séparateur virgule)")

parser_out = parser.add_argument_group("Paramètres des fichiers de sortie")
parser_out.add_argument('etu_path_out', help="chemin vers l'étude Crue10 à écrire (fichier etu.xml")
parser_out.add_argument('out_name', help="nom générique pour les scénario, modèle et sous-modèle (sans le suffixe)")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_merge_models(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
