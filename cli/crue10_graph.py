#!/usr/bin/env python
# coding: utf-8
"""
@brief:
Générer un schéma topologique sous forme d'image png/svg à partir d'une étude FC

@warnings:
Les fichiers de sortie sont écrasés s'ils existent

FIXME:
* les orifices ne sont pas orientés en réalité (Pb: avec le type de graph 'digraph' (DIrected graph) cela ne semble pas possible d'avoir les deux sur la double flèche)
"""
import argparse

from crue10.study import Study
from crue10.utils.graph_1d_model import *


parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
parser.add_argument("etu_path", help="fichier d'entrée etu.xml")
parser.add_argument("mo_name", help="nom du modèle")
parser.add_argument("--out_png", help="fichier de sortie au format png")
parser.add_argument("--out_svg", help="fichier de sortie au format svg")
parser.add_argument("--sep", help="ratio pour modifier l'espacement (par ex. 0.5 ou 2) [1 par défaut]", default=0.8)
args = parser.parse_args()


study = Study(args.etu_path)
model = study.get_model(args.mo_name)
model.read_all()
print(model)

try:
    import pydot
except:
    raise CrueError("Le module pydot ne fonctionne pas !")


# Create a directed graph
graph = pydot.Dot(graph_type='digraph', label=model.id, fontsize=MO_FONTSIZE, nodesep=args.sep)  # vertical : rankdir='LR'
for submodel in model.submodels:
    subgraph = pydot.Cluster(submodel.id, label=submodel.id, fontsize=SM_FONTSIZE,
                             style=key_from_constant(submodel.is_active, SM_STYLE))

    # Add nodes
    for _, noeud in submodel.noeuds.items():
        name = noeud.id
        connected_casier = submodel.get_connected_casier(noeud.id)
        has_casier = connected_casier is not None
        is_active = True
        if has_casier:
            is_active = connected_casier.is_active
            name += '\n(%s)' % connected_casier.id
        node = pydot.Node(noeud.id, label=name, fontsize=EMH_FONTSIZE, style="filled",
                          fillcolor=key_from_constant(is_active, NODE_COLOR),
                          shape=key_from_constant(has_casier, CASIER_SHAPE))
        subgraph.add_node(node)

    # Add branches
    for branche in submodel.iter_on_branches():
        edge = pydot.Edge(
            branche.noeud_amont.id, branche.noeud_aval.id, label=branche.id, fontsize=EMH_FONTSIZE,
            arrowhead=key_from_constant(branche.type, BRANCHE_ARROWHEAD),
            arrowtail=key_from_constant(branche.type, BRANCHE_ARROWHEAD),
            # arrowtail="inv",
            dir="forward",  # "both" or "back"
            style=key_from_constant(branche.is_active, BRANCHE_ARROWSTYLE),
            color=key_from_constant(branche.type, BRANCHE_COLORS),
            fontcolor=key_from_constant(branche.type, BRANCHE_COLORS),
            penwidth=key_from_constant(branche.type, BRANCHE_SIZE),
            # shape="dot"
        )
        subgraph.add_edge(edge)
    graph.add_subgraph(subgraph)

# Export(s) to png and/or svg
# prog='neato' optimizes space
if args.out_png:
    print("Génération du fichier {}".format(args.out_png))
    graph.write_png(args.out_png)
if args.out_svg:
    print("Génération du fichier {}".format(args.out_svg))
    graph.write_svg(args.out_svg)
# graph.write('debug.dot')
