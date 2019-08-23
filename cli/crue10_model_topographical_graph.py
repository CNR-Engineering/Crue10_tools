#!/usr/bin/env python
# coding: utf-8
"""
@brief:
Générer un schéma topologique sous forme d'image png/svg à partir d'un modèle d'une étude Crue10

@warnings:
Les fichiers de sortie sont écrasés s'ils existent
"""
import sys

from crue10.utils.cli_parser import MyArgParse
from crue10.utils import CrueError, logger
from crue10.study import Study


try:
    import pydot
except:
    logger.critical("Le module pydot ne fonctionne pas !")
    sys.exit(1)


def crue10_model_topographical_graph(args):
    study = Study(args.etu_path)
    model = study.get_model(args.mo_name)
    model.read_all()

    logger.info(model)
    model.write_topological_graph(args.out_files, nodesep=args.sep, prog=args.prog)


parser = MyArgParse(description=__doc__)
parser.add_argument("etu_path", help="fichier d'entrée etu.xml")
parser.add_argument("mo_name", help="nom du modèle")
parser.add_argument("out_files", help="fichier(s) de sortie (formats possibles: png, svg, dot...)", nargs='+')
parser.add_argument("--sep", help="ratio pour modifier l'espacement (par ex. 0.5 ou 2) [1 par défaut]", default=0.8)
parser.add_argument("--prog", help="outil de rendu", default='dot', choices=['dot', 'neato', 'fdp', 'sfdp'])


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_model_topographical_graph(args)
    except CrueError as e:
        logger.critical(e)
        sys.exit(1)
