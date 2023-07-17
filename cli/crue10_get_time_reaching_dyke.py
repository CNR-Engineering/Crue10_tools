#!/usr/bin/env python
# coding: utf-8
"""
Générer un fichier (.csv) permettant de connaître sur quelle section et à quel moment (temps en secondes)
le niveau d'eau dépasse le cavalier
"""
import pandas as pd
import numpy as np
import sys

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger
from crue10.utils.cli_parser import MyArgParse
from crue10.utils.settings import CSV_DELIMITER


def get_time_reaching_dyke(args):
    df_digues = pd.read_csv(args.dyke_path, sep=CSV_DELIMITER)
    etude = Etude(args.etu_path)

    if args.sc_name is None:
        scenario = etude.get_scenario_courant()
    else:
        scenario = etude.get_scenario(args.sc_name)

    if args.run_id is None:
        run = scenario.get_dernier_run()
    else:
        run = scenario.get_run(args.run_id)
    resultats = run.get_resultats_calcul()

    time = resultats.res_calc_trans[args.calc_trans].time_serie()

    export = []
    for section_id, z_digue, cavalier in zip(df_digues["Section"], df_digues["Digue"], df_digues["Cavalier"]):
        z_resultat = resultats.get_trans_var_at_emhs_as_array(args.calc_trans, 'Z', [section_id])
        time_above = np.where(z_resultat + cavalier > z_digue)[0]
        if len(time_above) != 0:
            first_time_above = time_above[0]
            export.append([section_id, z_resultat[first_time_above][0], z_digue, time[first_time_above]])

    df_export = pd.DataFrame(export, columns=["Section", "Cote_surface_libre", "Cote_digue", "Time_[s]"])
    df_export.to_csv(args.out_csv, sep=CSV_DELIMITER, index=False)


parser = MyArgParse(description=__doc__)
parser.add_argument('etu_path', help="chemin vers l'étude Crue10 à lire (fichier etu.xml)")
parser.add_argument('--sc_name', help="nom du scénario (avec le preffixe Sc_) (si absent alors le scénario courant est pris)")
parser.add_argument('--run_id', help="identifiant du Run à exploiter (si absent alors le dernier Run est pris)")
parser.add_argument('calc_trans', help="nom du calcul transitoire)")
parser.add_argument('dyke_path', help="chemin vers le fichier CSV avec les caractéristiques des digues")
parser.add_argument('out_csv', help="chemin vers le fichier CSV de sortie")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        get_time_reaching_dyke(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
