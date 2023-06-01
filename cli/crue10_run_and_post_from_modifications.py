#!/usr/bin/env python
# coding: utf-8
"""
Lance et exploite une simulation Crue10.

crue10_run_and_post_from_modifications.py etude.etu.xml inputs.csv outputs.csv
"""
import csv
import json
import random
import string
import sys
from time import perf_counter

from crue10.etude import Etude
from crue10.utils.cli_parser import MyArgParse
from crue10.utils import ExceptionCrue10, logger


def crue10_run_and_post_from_modifications(args):
    t0 = perf_counter()
    etude = Etude(args.etu_path)
    scenario = etude.get_scenario_courant()
    scenario.read_all()

    with open(args.inputs_json, 'r', encoding='utf-8') as filein:
        inputs = json.load(filein)
    # Convert to float
    for key, value in inputs.items():
        inputs[key] = float(value)

    scenario.apply_modifications(inputs)
    if args.random_run_ids:
        # /!\ NCNAME (XSD validation) should start by a letter
        run_id = random.choice(string.ascii_letters) + \
                ''.join(random.choice(string.ascii_letters + string.digits) for i in range(20))
    else:
        run_id = None
    run = scenario.create_and_launch_new_run(etude, run_id=run_id)

    with open(args.outputs_csv, 'w', newline='') as csvfile:
        fieldnames = ['variable', 'value']
        writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=fieldnames)
        writer.writeheader()

        if run.nb_erreurs() == 0:
            try:
                resultats = run.get_resultats_calcul()
            except Exception as e:
                logger.error(e)
                logger.warning("Les fichiers de résultats du Run `%s` ne sont pas exploitables" % run.id)
            res = resultats.get_data_pseudoperm(args.calc_name)
            pos_Z = resultats.variables['Section'].index('Z')
            values = res['Section'][:, pos_Z]
            t1 = perf_counter()
            writer.writerow({'variable': 'time_crue', 'value': run.get_time()})
            writer.writerow({'variable': 'time_total', 'value': t1 - t0})
            for emh_name, value in zip(resultats.emh['Section'], values):
                writer.writerow({'variable': emh_name, 'value': value})
        else:
            logger.warning("Le Run `%s` contient des erreurs et sera ignoré" % run.id)


parser = MyArgParse(description=__doc__)
parser.add_argument('etu_path', help="chemin vers l'étude Crue10 à lire (fichier etu.xml)")
parser.add_argument("inputs_json", help="fichier JSON d'entrée contenant les modifications à appliquer")
parser.add_argument("calc_name", help="nom du calcul permanent ou transitoire (si transitoire alors prend le max temporel)")
parser.add_argument("outputs_csv", help="fichier CSV de sortie")
parser.add_argument("--random_run_ids", help="nom de Run aléatoire (21 caractères alphanumériques)", action='store_true')


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_run_and_post_from_modifications(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
