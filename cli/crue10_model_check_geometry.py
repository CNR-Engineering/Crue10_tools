#!/usr/bin/env python
# coding: utf-8
"""
# Résumé
Vérifier la géométrie d'un modèle

# Détails
L'outil liste les problèmes potentiels en vérifiant les points suivants :
* branches de type orifice : PCS amont/aval plus profonds que le radier de l'ouvrage
* branches de type Strickler : PCS amont/aval plus profonds que le fond des profils amont/aval
"""
import sys

from crue10.emh.section import SectionIdem
from crue10.etude import Etude
from crue10.utils.cli_parser import MyArgParse
from crue10.utils import ExceptionCrue10, logger


def crue10_model_check_geometry(args):
    etude = Etude(args.etu_path)
    modele = etude.get_modele(args.mo_name)
    modele.read_all()

    for sous_modele in modele.liste_sous_modeles:
        logger.info("Vérification du %s" % sous_modele)

        # Vérification des branches orifice
        for branche in sous_modele.get_liste_branches([5]):
            for noeud, position in zip([branche.noeud_amont, branche.noeud_aval], ['amont', 'aval']):
                casier = sous_modele.get_connected_casier(noeud)
                if casier is not None:
                    if casier.get_min_z() > branche.Zseuil:
                        logger.error("Le casier %s %s n'est pas assez profond (Zmin=%f) par rapport"
                                     " à la branche orifice %s (Zseuil=%f)"
                                     % (position, casier.id, casier.get_min_z(), branche.id, branche.Zseuil))

        # Vérification des branches Strickler
        for branche in sous_modele.get_liste_branches([6]):
            for noeud, section, position in zip([branche.noeud_amont, branche.noeud_aval],
                                                [branche.get_section_amont(), branche.get_section_aval()], ['amont', 'aval']):
                casier = sous_modele.get_connected_casier(noeud)
                if casier is not None:
                    min_z = section.get_min_z()
                    if min_z < casier.get_min_z():
                        logger.error("La section %s %s est trop profonde (Zmin=%f) par rapport au casier %s (Zmin=%f)"
                                     % (position, section.id, min_z, casier.id, casier.get_min_z()))
                        branche.is_active = False


parser = MyArgParse(description=__doc__)
parser.add_argument('etu_path', help="chemin vers l'étude Crue10 à lire (fichier etu.xml)")
parser.add_argument("mo_name", help="nom du modèle (avec le preffixe Mo_)")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_model_check_geometry(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
