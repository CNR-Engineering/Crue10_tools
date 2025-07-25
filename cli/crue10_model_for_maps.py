#!/usr/bin/env python
# coding: utf-8
"""
Exporter les EMHs dans des fichiers shp pour CNR Maps
Les fichiers suivants sont créés :
- noeuds.shp
- casiers.shp
- branches.shp
- sections.shp
- sous-modeles.shp
- modele.shp

Remarques :
- Les EMHs inactives sont exportées
"""
from collections import OrderedDict
import fiona
import os.path
from shapely.geometry import mapping, Polygon
from shapely.ops import cascaded_union
import sys

from crue10.emh.branche import Branche
from crue10.emh.section import SectionProfil
from crue10.etude import Etude
from crue10.utils.cli_parser import MyArgParse
from crue10.utils import ExceptionCrue10, logger


def crue10_model_for_maps(args):
    study = Etude(args.etu_path)
    modele = study.get_modele(args.mo_name)
    modele.read_all()
    logger.info(modele.summary())

    if args.nom_modele:
        model_name = args.nom_modele
    else:
        model_name = modele.id

    if not os.path.exists(args.out_folder):
        os.makedirs(args.out_folder)

    # Noeuds
    schema = {
        'geometry': 'Point',
        'properties': OrderedDict([('NOM', 'str'), ('modele', 'str'), ('sousmodele', 'str')]),
    }
    with fiona.open(os.path.join(args.out_folder, 'noeuds.shp'), 'w', 'ESRI Shapefile', schema) as out_shp:
        for sous_modele in modele.liste_sous_modeles:
            for _, noeud in sous_modele.noeuds.items():
                layer = {
                    'geometry': mapping(noeud.geom),
                    'properties': {
                        'NOM': noeud.id,
                        'modele': model_name,
                        'sousmodele': sous_modele.id,
                    }
                }
                out_shp.write(layer)

    # Casiers
    schema = {
        'geometry': 'Polygon',
        'properties': OrderedDict([('NOM', 'str'), ('modele', 'str'), ('sousmodele', 'str'),
                                   ('noeud', 'str'), ('is_active', 'bool')]),
    }
    with fiona.open(os.path.join(args.out_folder, 'casiers.shp'), 'w', 'ESRI Shapefile', schema) as out_shp:
        for sous_modele in modele.liste_sous_modeles:
            for _, casier in sous_modele.casiers.items():
                layer = {
                    'geometry': mapping(Polygon(casier.geom)),
                    'properties': {
                        'NOM': casier.id,
                        'modele': model_name,
                        'sousmodele': sous_modele.id,
                        'noeud': casier.noeud_reference.id,
                        'is_active': casier.is_active,
                    }
                }
                out_shp.write(layer)

    # Branches
    schema = {
        'geometry': 'LineString',
        'properties': OrderedDict([('NOM', 'str'), ('modele', 'str'), ('sousmodele', 'str'), ('nd_amont', 'str'),
                                   ('nd_aval', 'str'), ('type', 'int'), ('is_active', 'bool')]),
    }
    with fiona.open(os.path.join(args.out_folder, 'branches.shp'), 'w', 'ESRI Shapefile', schema) as out_shp:
        for sous_modele in modele.liste_sous_modeles:
            for _, branche in sous_modele.branches.items():
                layer = {
                    'geometry': mapping(branche.geom),
                    'properties': {
                        'NOM': branche.id,
                        'modele': model_name,
                        'sousmodele': sous_modele.id,
                        'nd_amont': branche.noeud_amont.id,
                        'nd_aval': branche.noeud_aval.id,
                        'type': branche.type,
                        'is_active': branche.is_active,
                    }
                }
                out_shp.write(layer)

    # Sections
    schema = {
        'geometry': 'LineString',
        'properties': OrderedDict([('NOM', 'str'), ('modele', 'str'), ('sousmodele', 'str'),
                                   ('id_branche', 'str'), ('xp', 'float')]),
    }
    with fiona.open(os.path.join(args.out_folder, 'sections.shp'), 'w', 'ESRI Shapefile', schema) as out_shp:
        for sous_modele in modele.liste_sous_modeles:
            for section in sous_modele.get_liste_sections(section_type=SectionProfil, ignore_inactive=True):
                branche = sous_modele.get_connected_branche(section.id)
                layer = {
                    'geometry': mapping(section.geom_trace),
                    'properties': {
                        'NOM': section.id,
                        'modele': model_name,
                        'sousmodele': sous_modele.id,
                        'id_branche': branche.id if branche is not None else "",
                        'xp': section.xp,
                    }
                }
                out_shp.write(layer)

    # sous_modeles
    mo_geom_list = []
    schema = {
        'geometry': 'Polygon',
        'properties': OrderedDict([('NOM', 'str'), ('modele', 'str')]),
    }
    with fiona.open(os.path.join(args.out_folder, 'sous-modeles.shp'), 'w', 'ESRI Shapefile', schema) as out_shp:
        for sous_modele in modele.liste_sous_modeles:
            sous_modele.remove_sectioninterpolee()
            sous_modele.normalize_geometry()  # replace SectionIdem by SectionProfil

            sm_geom_list = []
            for _, casier in sous_modele.casiers.items():
                sm_geom_list.append(Polygon(casier.geom).buffer(args.sm_buffer))

            for branche in sous_modele.get_liste_branches():
                if branche.type in Branche.TYPES_WITH_GEOM:
                    # Build list of coordinates following upstream section, left ending points, downstream section and
                    #   right ending point
                    coords = []
                    coords += branche.get_section_amont().geom_trace.coords
                    for section in branche.liste_sections_dans_branche[1:-1]:
                        coords.append(section.geom_trace.coords[-1])
                    coords += reversed(branche.get_section_aval().geom_trace.coords)
                    for section in reversed(branche.liste_sections_dans_branche[1:-1]):
                        coords.append(section.geom_trace.coords[0])

                    polygon = Polygon(coords).buffer(args.sm_buffer)
                    if not polygon.is_valid:
                        raise RuntimeError
                    sm_geom_list.append(polygon)

                # Add geometry of the branch (necessary for branches without geometry)
                sm_geom_list.append(branche.geom.buffer(args.sm_buffer))

            for _, noeud in sous_modele.noeuds.items():
                sm_geom_list.append(noeud.geom.buffer(args.sm_buffer))

            mo_geom_list += sm_geom_list
            sm_zone = cascaded_union(sm_geom_list).simplify(args.dist_simplify)

            layer = {
                'geometry': mapping(sm_zone),
                'properties': {
                    'NOM': sous_modele.id,
                    'modele': model_name,
                }
            }
            out_shp.write(layer)

    # Modele
    schema = {
        'geometry': 'Polygon',
        'properties': OrderedDict([('NOM', 'str'), ('id_modele', 'str'), ('bief', 'str'),
                                   ('auteurs', 'str'), ('date', 'str')]),
    }
    with fiona.open(os.path.join(args.out_folder, 'modele.shp'), 'w', 'ESRI Shapefile', schema) as out_shp:
        mo_zone = cascaded_union(mo_geom_list).buffer(args.mo_buffer).simplify(args.dist_simplify)

        layer = {
            'geometry': mapping(mo_zone),
            'properties': {
                'NOM': model_name,
                'id_modele': modele.id,
                'bief': args.bief,
                'auteurs': args.auteurs,
                'date': args.date,
            }
        }
        out_shp.write(layer)


parser = MyArgParse(description=__doc__)
parser.add_argument('etu_path', help="chemin vers l'étude Crue10 à lire (fichier etu.xml)")
parser.add_argument('mo_name', help="nom du modèle (avec le preffixe Mo_)")
parser.add_argument('out_folder', help="chemin du dossier pour les fichiers shp de sortie")

parser_attributes = parser.add_argument_group("Arguments pour écrire les méta-données")
parser_attributes.add_argument('--nom_modele', help="nom du modèle", default='')
parser_attributes.add_argument('--bief', help="bigramme du bief", default='')
parser_attributes.add_argument('--auteurs', help="détails des auteurs", default='')
parser_attributes.add_argument('--date', help="date de valeur (format : JJ/MM/AAAA)", default='')

parser_geom = parser.add_argument_group("Arguments pour contrôler les polygone des sous-modèles et du modèle")
parser_geom.add_argument('--sm_buffer', help="distance de la zone tampon pour les sous-modèles (en m)", default=50.0)
parser_geom.add_argument('--mo_buffer', help="distance supplémentaire de la zone tampon pour le modèle (en m)",
                         default=100.0)
parser_geom.add_argument('--dist_simplify', help="distance de simplification des polygones (en m)", default=5.0)


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_model_for_maps(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
