#!/usr/bin/env python
# coding: utf-8
"""
# Résumé
Générer un schéma topologique sous forme d'image png/svg
à partir d'un modèle d'une étude Crue10

# Détails
* il s'agit d'une vue schématique avec tous les noeuds/casiers et les branches
    (aucune information géographique)
* l'orientation des branches correspond au sens de la ligne qui se termine par
    une flèche (branche fluviale) ou un symbole qui est "côté noeud aval"
    (la seule exception concerne les branches orifices dont la position du symbole
    tient compte du sens de l'orifice)
* les branches ou sous-modèles inactifs sont en pointillés
* la coloration des lignes dépend du type de branches
* la forme des noeuds et des casiers (avec leur nom associé) sont différentes
* le rendu du graphique est configurable avec les options `--sep` et `--prog`

# Avertissements
Les fichiers en sortie sont écrasés s'ils existent déjà
"""
import sys

from crue10.utils.cli_parser import MyArgParse
from crue10.utils import ExceptionCrue10, logger
from crue10.etude import Etude


def crue10_model_topographical_graph(args):
    study = Etude(args.etu_path)
    modele = study.get_modele(args.mo_name)
    modele.read_all()

    logger.info(modele)
    modele.write_topological_graph(args.out_files, nodesep=args.sep, prog=args.prog)


parser = MyArgParse(description=__doc__)
parser.add_argument('etu_path', help="chemin vers l'étude Crue10 à lire (fichier etu.xml)")
parser.add_argument("mo_name", help="nom du modèle (avec le preffixe Mo_)")
parser.add_argument("out_files", help="liste des fichier(s) à écrire (formats possibles : png, svg, dot)", nargs='+')
parser.add_argument("--sep", help="ratio pour modifier l'espacement (par ex. 0.5 ou 2)", default=0.8)
parser.add_argument("--prog", help="outil de rendu", default='dot', choices=['dot', 'neato', 'fdp', 'sfdp'])


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_model_topographical_graph(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
