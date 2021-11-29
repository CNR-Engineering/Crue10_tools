"""
IMPRES: DRS => ERS

Avec carte EXCEL

PROFR = Impressions des profils (version reduite)
PROFC =
"""
import pandas as pd

from crue9.utils import cvt_time_to_sec
from crue10.utils import ExceptionCrue10, logger


def split_line(line):
    return [l.strip() for l in line.split(';')]


def get_emh_names_in_impres(drs_path, cartes=['PROFR', 'PROFC']):
    """

    :param drs_path: chemin vers le fichier DRS
    :param cartes: nom des cartes
    :return:
    """
    emh_names = []
    with open(drs_path, 'r') as drs_in:
        for line in drs_in:
            line = line.strip()
            for carte in cartes:
                if line.startswith(carte):
                    emh_lst = line.split(' ')[1:]
                    emh_names = emh_names + emh_lst
    return emh_names


def read_impres_as_wide_df(ers_path, emh_names=None):
    """
    Extraction des résultats du fichier ERS au format dataframe large
    Prévu pour les cartes PROFC et PROFR

    :param ers_path: chemin vers le fichier ERS
    :param emh_names: nom des EMHs pour corriger la case
    :return: DataFrame avec les variables en colonne, le temps en secondes (time) et l'EMH
    :rtype: pd.Dataframe
    """
    if emh_names is not None:
        emh_names_upper = [name.upper() for name in emh_names]
    else:
        emh_names_upper = None

    with open(ers_path, 'r') as ers_in:
        lines = ers_in.readlines()

        df_res = pd.DataFrame()
        nb_emh = 0
        emh_name = None
        res = None
        var_names = []
        id_last_line = len(lines) - 1

        for i, line_str in enumerate(lines):
            line_str = line_str.replace('\n', '')
            line_lst = split_line(line_str)

            if 'Impressions des profils' in line_str:
                print(line_str)

            elif 'HEURES' == line_lst[0]:
                # Get variable names
                var_names = line_lst
                var_names[0] = 'time'  # rename first variable
                res = {var_name: [] for var_name in var_names}

            else:
                if len(line_lst) == len(var_names):
                    # Ligne avec des valeurs à un pas de temps donné
                    for j, (var_name, value) in enumerate(zip(var_names, line_lst)):
                        if j == 0:
                            res['time'].append(cvt_time_to_sec(value))
                        else:
                            res[var_name].append(float(value))

                if len(line_lst) == 1 or i == id_last_line:  # not elif for last line...
                    # Nouvelle section
                    if emh_name is not None:
                        df_append = pd.DataFrame(res)
                        df_append['emh'] = emh_name
                        df_res = df_res.append(df_append, ignore_index=True, sort=False)
                        res = {var_name: [] for var_name in var_names}

                    emh_name = line_lst[0]
                    if emh_names is not None and i != id_last_line:
                        try:
                            pos = emh_names_upper.index(emh_name)
                            emh_name = emh_names[pos]
                        except IndexError as e:
                            logger.debug("L'emh' `%s` n'a pas de correspondance (non sensible à la case) "
                                         "dans le liste fournie" % emh_name)

                    if i != id_last_line:
                        nb_emh += 1

                elif len(line_lst) != len(var_names):
                    raise ExceptionCrue10("La ligne `%s` ne contient pas %s variables"
                                          % (line_str, len(var_names)))

    return df_res
