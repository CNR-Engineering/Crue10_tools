#!/usr/bin/env python
# coding: utf-8
"""
Lance un run Crue10 complet.
"""
import sys

from crue10.etude import Etude
from crue10.utils.cli_parser import MyArgParse
from crue10.utils import ExceptionCrue10, logger


def crue10_run(args):
    etude = Etude(args.etu_path)
    if args.sc_name is None:
        scenario = etude.get_scenario_courant()
    else:
        scenario = etude.get_scenario(args.sc_name)
    scenario.read_all()

    if args.exe_path is None:
        run = scenario.create_and_launch_new_run(etude, run_id=args.run_id, force=args.force)
    else:
        run = scenario.create_and_launch_new_run(etude, run_id=args.run_id, exe_path=args.exe_path, force=args.force)
    etude.write_etu()

    print(run.get_all_traces_above_warn())
    print(run)


parser = MyArgParse(description=__doc__)
parser.add_argument('etu_path', help="chemin vers l'étude Crue10 à lire (fichier etu.xml)")
parser.add_argument("--sc_name", help="nom du scénario (si absent alors le scénario courant est considéré)")
parser.add_argument("--run_id", help="nom du run (si absent alors il prend correspond à l'horoàdatage du lancement)")
parser.add_argument("--exe_path", help="chemin vers l'exécutable Crue10")
parser.add_argument('-f', '--force', help="écraser le run s'il existe déjà", action='store_true')


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue10_run(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
