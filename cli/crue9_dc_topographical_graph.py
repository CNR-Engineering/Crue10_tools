#!/usr/bin/env python
# coding: utf-8
"""
# Résumé
Générer un schéma topologique sous forme d'image png/svg à partir d'un fichier dc
(fichier de géométrie de Crue 9)

# Détails
* il s'agit d'une vue schématique avec tous les noeuds/casiers et les branches
    (aucune information géographique)
* l'orientation des branches correspond au sens de la ligne qui se termine par
    une flèche (branche fluviale) ou un symbole qui est "côté noeud_reference aval"
* la coloration des lignes dépend du type de branches
* la forme des noeuds et des casiers (avec leur nom associé) sont différentes
* les parties commentées ou shunter (par un GOTO) sont ignorées
* les noms des branches et noeuds sont écrits en masjuscules
    (Crue9 n'étant pas sensible à la casse)
* les mots-clés (BRANCHE et GOTO) peuvent être indifférement
    en minuscules ou en majuscules.
* le rendu du graphique est configurable avec les options `--sep` et `--prog`

# Avertissements
Les fichiers en sortie sont écrasés s'ils existent déjà
"""
# Tout le fichier dc est lu et les variables affectées
# Ensuite l'arbre puis le graphique sont générés

from io import open  # Python2 fix
import sys

from crue10.utils import logger
from crue10.utils.cli_parser import MyArgParse
from crue10.utils.graph_1d_model import *


try:
    import pydot
except:
    logger.critical("Le module pydot ne fonctionne pas !")
    sys.exit(1)


def crue9_dc_topographical_graph(args):
    dc_file = args.fichier_dc
    with open(dc_file, 'r', encoding="ISO-8859-1") as filein:
        print("Traitement du fichier {}".format(dc_file))
        branches = {}  # dictionnaire de la forme {nom_branche: (noeud_amont, noeud_aval, type)}
        nodes = []  # liste des noeuds
        casiers = []  # liste des casiers
        label = None  # pour les goto

        for line in filein:
            line = line.replace('\n', '').strip()
            line = line.upper()  # nom des branches/noeuds (non-sensible à la casse)

            if not line.startswith('*'):
                if label is not None:
                    # Il y a un goto en cours...
                    if line.startswith(label):
                        print("/!\ Partie ignorée à cause du 'GOTO {}'".format(label))
                        label = None

                else:
                    # On est en dehors du goto
                    if line.startswith('GOTO'):
                        # Mais on rentre dans un autre GOTO...
                        (key, label) = line.split()

                    elif line.startswith('BRANCHE'):
                        # Une nouvelle branche est trouvée
                        (key, name, node_up, node_down, btype) = line.split()
                        btype = int(btype)
                        print("Ajout de la branche {} ({} -> {})".format(name, node_up, node_down))

                        # Ajout des noeuds si non présents
                        if node_up not in nodes:
                            nodes.append(node_up)
                        if node_down not in nodes:
                            nodes.append(node_down)

                        # Ajout de la branche
                        branches[name] = (node_up, node_down, btype)

                    elif line.startswith('CASIER'):
                        (key, node) = line.split()
                        casiers.append(node)
                        print("Casier {} détecté".format(node))

    # Create a directed graph
    # prog='neato' optimizes space
    graph = pydot.Dot(graph_type='digraph', nodesep=args.sep, prog=args.prog)  # vertical : rankdir='LR'

    # Add nodes
    for node in nodes:
        if node in casiers:
            has_casier = True
        else:
            has_casier = False
        graph.add_node(pydot.Node(node, fontsize=EMH_FONTSIZE, style="filled",
                                  fillcolor=key_from_constant(True, NODE_COLOR),
                                  shape=key_from_constant(has_casier, CASIER_SHAPE)))

    # Add branches
    for nom_branche, (node_up, node_down, btype) in branches.items():
        edge = pydot.Edge(
            node_up, node_down, label=nom_branche, fontsize=EMH_FONTSIZE,
            arrowhead=key_from_constant(btype, BRANCHE_ARROWHEAD),
            arrowtail=key_from_constant(btype, BRANCHE_ARROWHEAD),
            dir="forward",
            style=key_from_constant(True, BRANCHE_ARROWSTYLE),
            color=key_from_constant(btype, BRANCHE_COLORS),
            fontcolor=key_from_constant(btype, BRANCHE_COLORS),
            penwidth=key_from_constant(btype, BRANCHE_SIZE)
        )
        graph.add_edge(edge)

    # Export(s) to png, svg, dot...
    for out_file in args.out_files:
        if out_file:
            logger.debug("Génération du fichier %s (nodesep=%s, prog=%s)" % (out_file, args.nodesep, args.prog))
            if out_file.endswith('.png'):
                graph.write_png(out_file)
            elif out_file.endswith('.svg'):
                graph.write_svg(out_file)
            elif out_file.endswith('.dot'):
                graph.write_dot(out_file)
            else:
                raise CrueError("Le format de fichier de `%s` n'est pas supporté" % out_file)


parser = MyArgParse(description=__doc__)
parser.add_argument("fichier_dc", help="fichier d'entrée dc (format géométrie Crue9)")
parser.add_argument("out_files", help="liste des fichier(s) à écrire (formats possibles : png, svg, dot)", nargs='+')
parser.add_argument("--sep", help="ratio pour modifier l'espacement (par ex. 0.5 ou 2)", default=0.8)
parser.add_argument("--prog", help="outil de rendu", default='dot', choices=['dot', 'neato', 'fdp', 'sfdp'])


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue9_dc_topographical_graph(args)
    except CrueError as e:
        logger.critical(e)
        sys.exit(1)
