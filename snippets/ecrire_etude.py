# coding: utf-8
import logging
import os.path

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger


logger.setLevel(logging.INFO)


etu_path = os.path.join('out', 'Etu_from_scratch', 'Etu_from_scratch.etu.xml')

# Write an empty etude
etude_out = Etude(etu_path, mode='w')
etude_out.create_empty_scenario('Sc_from_scratch', 'Mo_from_scratch', 'Sm_from_scratch')
sous_modele_out = etude_out.get_sous_modele('Sm_from_scratch')

if True:
    # Add some EMHs in sous_modele
    from snippets.construire_et_ecrire_sous_modele import sous_modele
    sous_modele_out.ajouter_emh_depuis_sous_modele(sous_modele)

logger.info(etude_out.summary())
logger.info(etude_out.get_sous_modele('Sm_from_scratch').summary())
etude_out.get_modele('Mo_from_scratch').reset_initial_conditions()

logger.debug('-' * 32 + '\nValidation sous-modèle:')
sous_modele.log_validation()
etude_out.write_all()


# Read this new etude to check its integrity
etude_in = Etude(etu_path, mode='r')
try:
    etude_in.read_all()
    logger.debug('-' * 32 + '\nVérification ré-ouverture étude:')
    logger.info(etude_in.summary())
    logger.info(etude_in.get_sous_modele('Sm_from_scratch').summary())
except ExceptionCrue10 as e:
    logger.critical("Exception à l'ouverture de l'étude:\n%s" % e)


# XSD validation
etude_in.log_check_xml()
