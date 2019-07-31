"""
Lecture d'études Crue10 et vérification des fichiers XML
"""
from glob import glob
import os.path

from crue10.study import Study
from crue10.utils import CrueError, logger


for folder in glob(os.path.join('..', 'crue10_examples', 'Cas-tests', '*')):
    for etu_path in glob(os.path.join(folder, '*.etu.xml')):
        logger.info(etu_path)
        try:
            study = Study(etu_path)
            study.check_xml_files()
            study.read_all()

            # Write study
            out_folder = os.path.join('../tmp/Cas-tests', os.path.basename(etu_path)[:-8])
            study.write_all(out_folder)

            # Write topographical graph for each model
            for _, model in study.models.items():
                model.write_topological_graph([os.path.join(out_folder, model.id + '.png')])

        except CrueError as e:
            logger.critical(e)
