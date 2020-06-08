# coding: utf-8
"""
Lecture d'études Crue10 et vérification des fichiers XML de tous les modèles Conc

Bilan des différentes modifications du texte des fichiers introduites par le passage dans Crue10_tools.

TODO
"""
from glob import glob
import logging
import os.path

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger


logger.setLevel(logging.INFO)


for folder in glob(os.path.join('..', '..', 'Crue10_examples', 'sharepoint_modeles_Conc', '*')):
    for etu_path in glob(os.path.join(folder, '*.etu.xml')):
        logger.info(etu_path)
        try:
            etude = Etude(etu_path)
            try:
                etude.check_xml_files()
            except IOError:  # avoid some Crue9 missing files in `Etu_BV2016_Conc_Etatref - ISfonds2016_K2016`
                pass
            etude.read_all()

            # Write etude (to check in integrity, see difference in file docstring above)
            out_folder = os.path.join('..', 'tmp', 'sharepoint_modeles_Conc', os.path.basename(folder))
            etude.write_all(out_folder)

            # Write topographical graph for each modele
            # for _, modele in etude.modeles.items():
            #     modele.write_topological_graph([os.path.join(out_folder, modele.id + '.png')])

        except ExceptionCrue10 as e:
            logger.critical(e)
