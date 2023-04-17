# coding: utf-8
from collections import OrderedDict
from glob import glob
import logging
from multiprocessing import Pool
import numpy as np
import os
import pandas as pd

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger
from crue10.utils.settings import CRUE10_EXE_PATH, NCSIZE


def launch_scenario_modifications(function, modifications_liste, ncsize=NCSIZE):
    logger.info("Lancement de %i calculs en parallèle (sur %i processeurs)" % (len(modifications_liste), ncsize))
    with Pool(processes=ncsize) as pool:
        return pool.map(function, modifications_liste)


def launch_runs(dossier, scenarios_dict=None, crue_exe_dict={'prod': CRUE10_EXE_PATH}, overwrite=True):
    """
    :param dossier: dossier contenant des sous-dossiers avec un ou plusieurs .etu.xml
    :param scenarios_dict: dictionnaire avec les scénarios à lancer (mettre None pour prendre un scénario par défaut)
    :param crue_exe_dict: dictionnaire avec les coeurs à lancer (identifiant et chemin vers crue10.exe)
    :param overwrite: écrase les Run s'ils existent déjà
    :rtype: pd.DataFrame
    """
    LOGGER_LEVEL = logger.level
    df_runs = pd.DataFrame({'etude_dossier': [], 'etude_basename': [], 'scenario': [], 'exe_id': [],
                            'run_idx': [], 'run_id': [],
                            'variable': [], 'value': []})
    for folder in glob(os.path.join(dossier, '*')):
        etude_dossier = os.path.basename(folder)

        for etu_path in glob(os.path.join(folder, '*.etu.xml')):  # FIXME: only one etu.xml should be found by folder!
            if scenarios_dict is not None:
                try:
                    scenarios_dict[etude_dossier]
                except KeyError:
                    logger.error("Le dossier `%s` n'a pas de scénario spécifié et ne sera pas traité"
                                 % etude_dossier)
                    continue

            try:
                etude = Etude(etu_path)
                logger.info(">>>>>>>>>> Dossier étude: %s <<<<<<<<<<" % etude_dossier)

                logger.setLevel(logging.ERROR)
                etude.read_all()
                logger.setLevel(LOGGER_LEVEL)

                if scenarios_dict is None:
                    # Consider all scenarios
                    scenario_names = etude.scenarios
                else:
                    scenario_name = scenarios_dict[etude_dossier]
                    if scenario_name is None:
                        scenario_name = etude.nom_scenario_courant
                    scenario_names = [scenario_name]

                for scenario_name in scenario_names:
                    scenario = etude.get_scenario(scenario_name)
                    logger.info("%s: %i calculs" % (etu_path, scenario.get_nb_calc_pseudoperm_actif()))

                    # Shift 'prod' to the end to call `normalize_for_g1_2_1` safely
                    if 'prod' in crue_exe_dict:
                        value = crue_exe_dict.pop('prod')
                        crue_exe_dict['prod'] = value

                    for run_idx, (exe_id, crue10_exe) in enumerate(crue_exe_dict.items()):
                        if exe_id == 'prod':
                            scenario.normalize_for_g1_2_1()

                        values = OrderedDict()

                        run_id = scenario_name[3:] + '_' + exe_id
                        run_id = run_id[:32]  # avoid error with too long identifier
                        if not overwrite and run_id in scenario.runs:
                            # Load existing run
                            run = scenario.get_run(run_id)
                        else:
                            try:
                                run = scenario.create_and_launch_new_run(etude, run_id=run_id, exe_path=crue10_exe,
                                                                         force=overwrite)
                                etude.write_etu()
                            except ExceptionCrue10 as e:
                                logger.error("Erreur de calcul pour le Run #%s\n%s" % (run_id, e))
                                etude.write_etu()
                                continue
                        logger.info(run)

                        # Get nb_calc_perm
                        try:
                            resultats = run.get_resultats_calcul()
                            values['nb_calc_perm'] = len(resultats.res_calc_pseudoperm)
                        except IOError as e:
                            logger.warning("Aucun résultat trouvé (fichier rcal manquant) pour le Run #%s" % run_id)
                            values['nb_calc_perm'] = 0

                        # Compute nb_services_ok
                        nb_services_ok = 0
                        for service, traces in run.traces.items():
                            if traces and run.nb_erreurs_bloquantes([service]) == 0:
                                if service == 'r':
                                    # Display a message to check Crue10 version
                                    logger.debug("%s: %s" % (exe_id, traces[0].get_message()))
                                nb_services_ok += 1

                        # Save criteria in values and append them in df_runs
                        values.update(OrderedDict([
                            ('nb_services_ok', nb_services_ok),
                            ('nb_erreurs_calculs', run.nb_erreurs_calcul()),
                            ('nb_avertissements_calculs', run.nb_avertissements_calcul()),
                        ]))
                        for var, value in values.items():
                            df_append = pd.Series({
                                'etude_dossier': etude_dossier, 'etude_basename': os.path.basename(etu_path),
                                'scenario': scenario_name, 'exe_id': exe_id,
                                'run_idx': run_idx, 'run_id': run_id,
                                'variable': var, 'value': value
                            })
                            df_runs = df_runs.append(df_append, ignore_index=True)

            except ExceptionCrue10 as e:
                logger.critical("ERREUR CRITIQUE :\n%s" % e)

    return df_runs


def get_run_steady_results(dossier, df_runs_unique, reference, out_csv_diff_by_calc=None,
                           variable='Z', emh_type='Section'):
    """
    :param dossier: dossier contenant des sous-dossiers avec un ou plusieurs .etu.xml
    :param df_runs_unique:
    :param reference:
    :param variable:
    :param emh_type:
    :rtype: pd.DataFrame
    """
    # Sort df_runs_unique to have 'prod' in first position to compute differences
    df_runs_unique = df_runs_unique.sort_values(['etude_dossier', 'scenario', 'exe_id'],
                                                ascending=[True, True, True])

    LOGGER_LEVEL = logger.level
    res_perm = {}
    cols = list(df_runs_unique.columns)
    df_diff_stat = pd.DataFrame({col: [] for col in cols + ['variable', 'value']})
    etu_path_last = ''
    for _, row in df_runs_unique.iterrows():
        # Build a Study instance
        etude_dossier = row['etude_dossier']
        etu_path = os.path.join(dossier, etude_dossier, row['etude_basename'])
        if etu_path != etu_path_last:
            logger.info(">>>>>>>>>> Dossier étude: %s <<<<<<<<<<" % etude_dossier)
            etude = Etude(etu_path)

        # Get a Scenario instance and read its data
        scenario = etude.get_scenario(row['scenario'])
        logger.setLevel(logging.ERROR)
        scenario.read_all()
        logger.setLevel(LOGGER_LEVEL)

        # Get a Run instance and read all steady results
        run = scenario.get_run(row['run_id'])
        logger.info(run)
        try:
            resultats = run.get_resultats_calcul()
        except IOError as e:
            logger.error("Un fichier de sortie du Run `%s` manque: %s" % (run.id, e))
            continue
        key = (scenario.id, row['exe_id'])
        res_perm_curr = resultats.get_res_all_pseudoperm_var_at_emhs(variable, resultats.emh[emh_type])
        res_perm[key] = res_perm_curr

        # Get reference results to compute differences
        try:
            res_perm_ref = res_perm[(scenario.id, reference)]
        except KeyError:
            logger.error("Les résultats de la référence `%s` n'existent pas "
                         "(%s manquant ou résultats non exploitable)" % (reference, scenario))
            continue
        # TODO : ajouter transitoire?

        # Compute difference on available results
        nb_common_calc = int(res_perm_ref.shape[0])
        if res_perm_curr.shape[0] != res_perm_ref.shape[0]:
            nb_common_calc = min(int(res_perm_curr.shape[0]), int(res_perm_ref.shape[0]))
            if nb_common_calc == 0:
                logger.error("Aucun calcul en commun, les résultats ne peuvent pas être comparés")
                continue
            res_perm_curr = res_perm_curr[:nb_common_calc, :]
            res_perm_ref = res_perm_ref[:nb_common_calc, :]
        diff = res_perm_curr - res_perm_ref
        diff_abs = np.abs(diff)

        nb_calc_perm = len(resultats.res_calc_pseudoperm)
        if out_csv_diff_by_calc is not None and row['exe_id'] == 'qualif':
            df_diff = pd.DataFrame({
                'id_calcul': np.repeat(np.arange(nb_common_calc, dtype=np.int64) + 1, diff.shape[1]),
                'emh': resultats.emh[emh_type] * diff.shape[0],
                'diff': diff.flatten()
            })
            df_diff.to_csv(out_csv_diff_by_calc % etude_dossier, sep=';', index=False)

        # Compute criteria
        values = OrderedDict([
            ('MSD', np.mean(diff)),
            ('MAD', np.mean(diff_abs)),
            ('DIFF_ABS_MAX', diff_abs.max()),
            ('RMSD', np.sqrt(np.mean(diff ** 2))),
        ])

        # Append criteria in df_diff_stat
        metadata = dict(row)
        for var, value in values.items():
            metadata.update({'variable': var, 'value': value})
            df_diff_stat = df_diff_stat.append(pd.Series(metadata), ignore_index=True)

        # Save current etu_path to avoid reading again at next loop iteration
        etu_path_last = etu_path

    return df_diff_stat
