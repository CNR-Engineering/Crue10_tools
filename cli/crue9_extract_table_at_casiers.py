#!/usr/bin/env python
# coding: utf-8
"""
Extraire un tableau pour un Run en transitoire avec comme colonne :
- emh: nom de l'EMH
- Q: débit maximum (m3/s)
- Z: niveau maximum (mNGF)
- surf(m2): surface (m²)
- vol.(mm3): volume (m³)
- hmoy : hauteur moyenne maximum, calculée comme ratio Vol/Splan (m)

Pour avoir un fichier ERS exploitable, il faut appeler IMPRES avec la carte `EXCEL` et une série de cartes `CASIER`
dans le fichier DRS.
"""
import numpy as np
import sys

from crue9.impres import read_impres_as_wide_df

from crue10.utils import ExceptionCrue10, logger
from crue10.utils.cli_parser import MyArgParse


VARNAME_SPLAN = 'surf(m2)'
VARNAME_VOLUME = 'vol.(mm3)'


def crue9_extract_table_at_casiers(args):
    # Read IMPRES result file
    df_wide = read_impres_as_wide_df(args.ers_path)
    df_wide['hmoy'] = np.divide(df_wide[VARNAME_VOLUME] * 1e9, df_wide[VARNAME_SPLAN],
                                out=np.zeros_like(df_wide[VARNAME_VOLUME]), where=df_wide[VARNAME_SPLAN] != 0)
    df_wide = df_wide.drop('time', axis=1)

    # Aggregate over time (compute max)
    df_max = df_wide.groupby(by='emh').max()
    df_max.to_csv(args.csv_path, sep=';')


parser = MyArgParse(description=__doc__)
parser.add_argument('ers_path', help="chemin vers le fichier ERS à lire (fichier .ERS)")
parser.add_argument('csv_path', help="chemin vers le fichier CSV de sortie")


if __name__ == '__main__':
    args = parser.parse_args()
    try:
        crue9_extract_table_at_casiers(args)
    except ExceptionCrue10 as e:
        logger.critical(e)
        sys.exit(1)
