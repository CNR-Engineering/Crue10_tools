# coding: utf-8
from glob import glob
from logging import INFO
import os.path

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger


# logger.setLevel(INFO)

DOSSIER = 'Cas-tests'
# DOSSIER = 'sharepoint_modeles_Conc'
grammaire_cible = '1.3'

dossier = 'C:/PROJETS/python/Crue10_examples/%s' % DOSSIER
dossier_new = 'C:/PROJETS/python/Crue10_examples/%s_g%s' % (DOSSIER, grammaire_cible)

for folder in glob(os.path.join(dossier, '*')):
    etude_dossier = os.path.basename(folder)

    logger.debug('\n\n')
    for etu_path in glob(os.path.join(folder, '*.etu.xml')):  # FIXME: only one etu.xml should be found by folder!
        etude = Etude(etu_path)

        # Lecture d'un maximum de sous-modèles
        for sous_modele in etude.get_liste_sous_modeles():
            try:
                sous_modele.read_all()
                sous_modele.changer_version_grammaire(grammaire_cible)
            except ExceptionCrue10 as e:
                del etude.sous_modeles[sous_modele.id]
                logger.critical("ERREUR CRITIQUE pour %s:\n%s" % (sous_modele, e))

        # Lecture d'un maximum de modèles
        for modele in etude.get_liste_modeles():
            try:
                modele.read_all()
                modele.changer_version_grammaire(grammaire_cible, shallow=True)
            except ExceptionCrue10 as e:
                del etude.modeles[modele.id]
                logger.critical("ERREUR CRITIQUE pour %s:\n%s" % (modele, e))

        # Lecture d'un maximum de scénarios
        for scenario in etude.get_liste_scenarios():
            try:
                scenario.read_all()
                scenario.changer_version_grammaire(grammaire_cible, shallow=True)
            except ExceptionCrue10 as e:
                del etude.scenarios[scenario.id]
                logger.critical("ERREUR CRITIQUE pour %s:\n%s" % (scenario, e))

        etude.was_read = True
        etude.move(os.path.join(dossier_new, os.path.basename(folder)))
        try:
            etude.changer_version_grammaire(grammaire_cible, shallow=True)
            etude.write_all()
        except ExceptionCrue10 as e:
            logger.critical("ERREUR CRITIQUE pour %s:\n%s" % (etude, e))
