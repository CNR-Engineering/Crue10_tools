# coding: utf-8
import logging
import os.path

from crue10.study import Study
from crue10.utils import logger

logger.setLevel(logging.DEBUG)


etu_path = os.path.join('out', 'Etu_from_scratch', 'Etu_from_scratch.etu.xml')

# Write an empty study
study_out = Study(etu_path, access='w')
study_out.create_empty_scenario('Sc_from_scratch', 'Mo_from_scratch', 'Sm_from_scratch')
submodel_out = study_out.get_submodel('Sm_from_scratch')

if True:
    # Add some EMHs in submodel
    from snippets.write_submodel_from_scratch import submodel
    submodel_out.add_emh_from_submodel(submodel)

logger.info(study_out.summary())
logger.info(study_out.get_submodel('Sm_from_scratch').summary())
study_out.get_model('Mo_from_scratch').reset_initial_conditions()
study_out.write_all()


# Read this new study to check its integrity
study_in = Study(etu_path, access='r')
study_in.read_all()
logger.info(study_in.summary())
logger.info(study_in.get_submodel('Sm_from_scratch').summary())
