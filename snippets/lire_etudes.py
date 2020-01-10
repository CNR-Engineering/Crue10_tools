# coding: utf-8
"""
Lecture d'études Crue10 et vérification des fichiers XML

Bilan des différentes modifications du texte des fichiers introduites par le passage dans Crue10_tools.

# BE2016_conc
OK

# Etu_BV2016_Conc_Etatref - ISfonds2016_K2016
- dlhy: &apos; => '
- drso: some empty `Commentaire` tags appear as they were missing

# GE2009_Conc
- dclm: &apos; => '
(Sur Windows ou Python2 sur Linux: drso: some Xp are truncated)

# VA2018_Conc
OK (sauf copie manquante des fichiers orphelins)
(Sur Windows ou Python2 sur Linux: drso: some Xp are truncated)
"""
from glob import glob
import os.path

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger


for folder in glob(os.path.join('..', '..', 'Crue10_examples', 'Etudes-tests', '*')):
    for etu_path in glob(os.path.join(folder, '*.etu.xml')):
        logger.info(etu_path)
        try:
            study = Etude(etu_path)
            try:
                study.check_xml_files()
            except IOError:  # avoid some Crue9 missing files in `Etu_BV2016_Conc_Etatref - ISfonds2016_K2016`
                pass
            study.read_all()

            # Write etude (to check in integrity, see difference in file docstring above)
            out_folder = os.path.join('../tmp/Etudes-tests', os.path.basename(folder))
            study.write_all(out_folder)

            # Write topographical graph for each modele
            # for _, modele in etude.modeles.items():
            #     modele.write_topological_graph([os.path.join(out_folder, modele.id + '.png')])

        except ExceptionCrue10 as e:
            logger.critical(e)
