"""
Lecture d'études Crue10 et vérification des fichiers XML
"""
from glob import glob
import os.path
import sys

from crue10.utils import CrueError, logger
from crue10.study import Study


for folder in glob(os.path.join('..', 'SHY_C10_Crue10', 'Cas-tests', '*')):
    for etu_path in glob(os.path.join(folder, '*.etu.xml')):
        print(etu_path)
        try:
            study = Study(etu_path)
            study.check_xml_files()
            #study.read_all()
            print("COUCOU")
            print(study.scenarios)
            # for _, sc in study.scenarios.items():
            #     print(sc.files)
            #study.write_all(os.path.join('../tmp', 'SHY_C10_Crue10', study.folder))

        except CrueError as e:
            logger.critical(e)

        break
    break
