#!/usr/bin/env python
# coding: utf-8
"""
Lance et exploite une simulation Crue10.

crue10_run_and_post_from_modifications.py etude.etu.xml inputs.csv outputs.csv
"""
import csv
import json
import sys

from crue10.etude import Etude
from crue10.utils.cli_parser import MyArgParse
from crue10.utils import ExceptionCrue10, logger


def crue10_run_and_post_from_modifications(args):
    etude = Etude(args.etu_path)
    scenario = etude.get_scenario_courant()
    scenario.read_all()

    with open(args.inputs_json, 'r', encoding='utf-8') as filein:
        inputs = json.load(filein)
    # Convert to float
    for key, value in inputs.items():
        inputs[key] = float(value)

    scenario.apply_modifications(inputs)
    run = scenario.create_and_launch_new_run(etude)

    with open(args.outputs_csv, 'w', newline='') as csvfile:
        fieldnames = ['emh_name', 'Z']
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
        writer.writeheader()

        if run.nb_erreurs() == 0:
            try:
                results = run.get_results()
            except Exception as e:
                logger.error(e)
                logger.warn("Les fichiers de résultats du Run `%s` ne sont pas exploitables" % run.id)
            res = results.get_res_steady(args.calc_name)
            pos_Z = results.variables['Section'].index('Z')
            values = res['Section'][:, pos_Z]
            for emh_name, value in zip(results.emh['Section'], values):
                writer.writerow({'emh_name': emh_name, 'Z': value})
        else:
            logger.warn("Le Run `%s` contient des erreurs et sera ignoré" % run.id)


parser = MyArgParse(description=__doc__)
parser.add_argument('etu_path', help="chemin vers l'étude Crue10 à lire (fichier etu.xml)")
parser.add_argument("inputs_json", help="fichier JSON d'entrée contenant les modifications à appliquer")
parser.add_argument("calc_name", help="nom du calcul permanent ou transitoire (si transitoire alors prend le max temporel)")
parser.add_argument("outputs_csv", help="fichier CSV de sortie")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_run_and_post_from_modifications(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
