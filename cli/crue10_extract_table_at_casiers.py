#!/usr/bin/env python
# coding: utf-8
"""
Extraire un tableau pour un Run en transitoire :
- zfond : point le plus bas du casier (issu de la géométrie des PCS)
- zmax : niveau maximum
- hmoy : hauteur moyenne maximum, calculée comme ratio Vol/Splan

Il faut que les variables Z, Vol et Splan soient disponibles aux casiers.
"""
import numpy as np
import pandas as pd
import sys

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger
from crue10.utils.cli_parser import MyArgParse


def crue10_extract_table_at_casiers(args):
    # Read Scenario
    etude = Etude(args.etu_path)
    if args.sc_name is None:
        scenario = etude.get_scenario_courant()
    else:
        scenario = etude.get_scenario(args.sc_name)
    scenario.read_all()

    # Get results at Casiers
    if args.run_id is None:
        run = scenario.get_last_run()
    else:
        run = scenario.get_run(args.run_id)
    results = run.get_results()
    res_trans = results.get_res_unsteady(args.calc_unsteady)

    emh_names = results.emh['Casier']
    variables = results.variables['Casier']
    res = res_trans['Casier']

    # Check if variables exist at Casiers
    try:
        pos_Z = variables.index('Z')
        pos_Vol = variables.index('Vol')
        pos_Splan = variables.index('Splan')
    except ValueError as e:
        logger.critical("Au moins une variable aux casiers est manquante : %s" % e)
        sys.exit(2)

    # Select time range
    time = results.get_calc_unsteady(args.calc_unsteady).time_serie()
    res = res[np.logical_and(args.start_time <= time, time <= args.end_time), :, :]

    # Compute Vol/Splan (except when Splan=0 to avoid division by zero) and extract the max over the time
    hmoy = np.max(np.divide(res[:, :, pos_Vol], res[:, :, pos_Splan],
                            out=np.zeros_like(res[:, :, pos_Vol]), where=res[:, :, pos_Splan] != 0),
                  axis=0)

    df = pd.DataFrame({
        'emh_name': emh_names,
        'zfond': [scenario.modele.get_casier(ca_name).get_min_z() for ca_name in emh_names],
        'zmax': np.max(res[:, :, pos_Z], axis=0),
        'hmoy': hmoy,
        # 'Volmax': np.max(res[:, :, pos_Vol], axis=0),
        # 'Splanmax': np.max(res[:, :, pos_Splan], axis=0),
    })
    df.to_csv(args.csv_path, sep=';')


parser = MyArgParse(description=__doc__)
parser.add_argument('etu_path', help="chemin vers l'étude Crue10 à lire (fichier etu.xml)")
parser.add_argument('--sc_name', help="nom du scénario (avec le preffixe Sc_) (si absent alors le scénario courant est pris)")
parser.add_argument('--run_id', help="identifiant du Run à exploiter (si absent alors le dernier Run est pris)")
parser.add_argument('--start_time', help="premier temps (en secondes) à considérer", type=float, default=-float('inf'))
parser.add_argument('--end_time', help="dernier temps (en secondes) à considérer", type=float, default=float('inf'))
parser.add_argument('calc_unsteady', help="nom du calcul transitoire")
parser.add_argument('csv_path', help="chemin vers le fichier CSV de sortie")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_extract_table_at_casiers(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
