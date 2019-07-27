#!/usr/bin/env python
# coding: utf-8
"""
@brief:
Générer un schéma topologique sous forme d'image png/svg à partir d'un modèle d'une étude Crue10

@warnings:
Les fichiers de sortie sont écrasés s'ils existent

FIXME:
* les orifices ne sont pas orientés en réalité (Pb: avec le type de graph 'digraph' (DIrected graph) cela ne semble pas possible d'avoir les deux sur la double flèche)
"""
import argparse

from crue10.study import Study


parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
parser.add_argument("etu_path", help="fichier d'entrée etu.xml")
parser.add_argument("mo_name", help="nom du modèle")
parser.add_argument("out_files", help="fichier(s) de sortie (formats possibles: png, svg, dot...)", nargs='+')
parser.add_argument("--sep", help="ratio pour modifier l'espacement (par ex. 0.5 ou 2) [1 par défaut]", default=0.8)
parser.add_argument("--prog", help="outil de rendu", default='dot', choices=['dot', 'neato', 'fdp', 'sfdp'])
args = parser.parse_args()


study = Study(args.etu_path)
model = study.get_model(args.mo_name)
model.read_all()
print(model)
model.write_topological_graph(args.out_files, nodesep=args.sep, prog=args.prog)
