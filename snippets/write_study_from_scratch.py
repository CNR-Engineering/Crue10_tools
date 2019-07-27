import logging

from crue10.study import Study
from crue10.utils import logger

logger.setLevel(logging.DEBUG)


# Write an empty study
study_out = Study('Etu_vierge.etu.xml', access='w')
study_out.create_empty_scenario('Sc_vierge', 'Mo_vierge', 'Sm_vierge', comment='Modèle vierge')
empty_submodel = study_out.get_submodel('Sm_vierge')

if True:
    # Add some EMHs in submodel
    from snippets.write_submodel_from_scratch import submodel
    empty_submodel.add_emh_from_submodel(submodel)

print(study_out.summary())
print(study_out.get_submodel('Sm_vierge').summary())
study_out.write_all('../tmp/Etu_vierge')


# Read this new study to check its integrity
study_in = Study('../tmp/Etu_vierge/Etu_vierge.etu.xml', access='r')
study_in.read_all()
print(study_in.summary())
print(study_in.get_submodel('Sm_vierge').summary())
