# coding: utf-8
import logging
import os.path

from crue10.etude import Etude
from crue10.utils import logger

logger.setLevel(logging.DEBUG)


etu_path = os.path.join('out', 'Etu_from_scratch', 'Etu_from_scratch.etu.xml')

# Write an empty etude
study_out = Etude(etu_path, access='w')
study_out.create_empty_scenario('Sc_from_scratch', 'Mo_from_scratch', 'Sm_from_scratch')
sous_modele_out = study_out.get_sous_modele('Sm_from_scratch')

if True:
    # Add some EMHs in sous_modele
    from snippets.construire_et_ecrire_sous_modele import sous_modele
    sous_modele_out.ajouter_emh_depuis_sous_modele(sous_modele)

logger.info(study_out.summary())
logger.info(study_out.get_sous_modele('Sm_from_scratch').summary())
study_out.get_modele('Mo_from_scratch').reset_initial_conditions()
study_out.write_all()


# Read this new etude to check its integrity
study_in = Etude(etu_path, access='r')
study_in.read_all()
logger.info(study_in.summary())
logger.info(study_in.get_sous_modele('Sm_from_scratch').summary())
