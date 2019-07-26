import logging

from crue10.study import Study
from crue10.utils import logger

logger.setLevel(logging.DEBUG)


# Write an empty study
study = Study('Etu_vierge.etu.xml', access='w')
study.create_empty_scenario('Sc_vierge', 'Mo_vierge', 'Sm_vierge', comment='Modèle vierge')
empty_submodel = study.get_submodel('Sm_vierge')

if True:
    # Add some EMHs in submodel
    from snippets.write_submodel_from_scratch import submodel
    empty_submodel.add_emh_from_submodel(submodel)

print(study.summary())
print(study.get_submodel('Sm_vierge').summary())
study.write_all('../tmp/Etu_vierge')


# Read this study to check its integrity
study2 = Study('../tmp/Etu_vierge/Etu_vierge.etu.xml', access='r')
study2.read_all()
print(study2.summary())
print(study2.get_submodel('Sm_vierge').summary())
