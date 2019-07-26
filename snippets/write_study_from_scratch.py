import logging

from crue10.study import Study
from crue10.utils import logger

logger.setLevel(logging.DEBUG)


# Write an empty study
study = Study('../tmp/Etu_vierge/Etu_vierge.etu.xml', access='w')
study.create_empty_scenario('Sc_vierge', 'Mo_vierge', 'Sm_vierge', comment='Modèle vierge')
print(study.summary())
study.write_all()
