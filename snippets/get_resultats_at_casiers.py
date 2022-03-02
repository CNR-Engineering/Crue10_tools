import pandas as pd

from crue10.emh.branche import BrancheSeuilLateral, BrancheOrifice, BrancheStrickler
from crue10.etude import Etude


etude = Etude('C:/DATA/FC/v1.2.1/CA2020-tourneEP20zonage_v5/Etu_CA2020_Conc.etu.xml')
scenario = etude.get_scenario_courant()
scenario.read_all()
sous_modele = scenario.modele.get_sous_modele('Sm_CA2020')
print(sous_modele.validate())

run = scenario.get_last_run()
results = run.get_results()
print("RUN=%s" % run.id)
print(results.summary())

casier_names = results.emh['Casier']
res = results.get_res_all_steady_var_at_emhs('Z', casier_names)

df_time = pd.DataFrame(results.calc_steady_dict.keys(), columns=['calcul'])
df_res = pd.DataFrame(res, columns=casier_names)

df_all = pd.concat([df_time, df_res], axis=1)
df_all.to_csv('casiers_abs.csv', sep=';')

df_min = df_res.min(axis=0)
df_max = df_res.max(axis=0)
df_rel = (df_res - df_min)/(df_max - df_min)


df_inondation = pd.DataFrame()
for casier_name in casier_names:
    if df_rel[casier_name].isnull().values.any():
        print(casier_name)
        noeud = sous_modele.get_casier(casier_name).noeud_reference
        branches = sous_modele.get_connected_branches(noeud.id)

        for branche in branches:
            if branche.is_active:
                if noeud.id == branche.noeud_amont.id:
                    noeud_amont = branche.noeud_aval
                else:
                    noeud_amont = branche.noeud_amont
                z_amont = results.get_res_all_steady_var_at_emhs('Z', [noeud_amont.id])[-1][0]

                if isinstance(branche, BrancheSeuilLateral):
                    z_tn = branche.get_min_z()
                elif isinstance(branche, BrancheOrifice):
                    z_tn = branche.Zseuil
                elif isinstance(branche, BrancheStrickler):
                    z_tn = max(branche.get_section_amont().get_min_z(), branche.get_section_aval().get_min_z())
                else:
                    raise NotImplementedError("Type de branche non supporté: %i" % branche.type)

                df_append = pd.Series({'casier': casier_name, 'branche': branche.id, 'noeud_amont': noeud_amont.id,
                                       'z_tn': z_tn, 'z_amont': z_amont, 'diff': z_tn - z_amont})
                df_inondation = df_inondation.append(df_append, ignore_index=True)

df_all = pd.concat([df_time, df_rel], axis=1)
df_all.to_csv('casiers_rel.csv', sep=';')

df_inondation = df_inondation.sort_values(['diff', 'casier'])
df_inondation.to_csv('casiers_inondation_%s.csv' % run.id, sep=';')
