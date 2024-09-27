Journal des modifications
=========================

## [X.X] en cours
- Prise en compte du déplacement de Pm_TolStQ du CCM vers le OPTI pour les initialisations de type Saint-Venant (g1.3)
- Amélioration performances lecture binaire en utilisant `np.frombuffer` (au lieu de struct)
- Correction plantage lecture RCAL si aucun résultat aux branches


## [4.1] - 2024-05-24

### Nouveautés
- Ajout `Etude.renommer_sous_modele`

### Corrections
- Ajout des fichiers de données dans le package Python (via MANIFEST.in)
- `stat_diff_calculs_{Cas-tests,Conc}.py` se lisent un Run OTFA
- Remplacement `np.float` et `np.int` qui ont expirés (avec numpy 1.24)
- Mise à jour des fichiers XSD et CCM


## [4.0] - 2023-06-01

### Nouveautés
- Support en lecture/écriture des grammaires v1.2 et v1.3 :
    * ajout de 2 variables utilisateurs : `VERSION_GRAMMAIRE_PRECEDENTE` et `VERSION_GRAMMAIRE_COURANTE`
    * possibilité de changer de grammaire avec `changer_version_grammaire`
- Vérification de la dimension/taille des array 2D pour les méthodes de type "set"
- Ajout de tests unitaires (dans `crue10/tests`)

Détails :
* Les grammaires doivent être identiques en lecture pour chaque Etude/Scenario/Modele/SousModele (plantage sinon)

### Changements
- Refactoring :
    * `crue10.base` : la classe `FichierXML` devient `EnsembleFichiersXML`, son attribut `access` devient `mode`
        (par héritage, l'attribut change aussi pour `Etude`, `Scenario`, `Modele`, `SousModele`, `FichierOtfa`)
    * `crue10.emh.branche` :
        * les propriétés du type `name_loi_*` deviennent `nom_loi_*`
        * `BarrageFilEau` :
            * l'attribut `comment_denoye` devient `comment_manoeuvrant`
            * la méthode `set_liste_elements_seuil_avec_coeff_par_defaut` devient `set_liste_elements_seuil_avec_coef_par_defaut`
            * [MAJEUR] l'attribut `loi_QZam` devient `loi_QpilZam`
            * [MAJEUR] l'attribut `liste_elements_seuil` devient `liste_elements_barrage`
            * [MAJEUR] la méthode `set_loi_QZam` devient `set_loi_QpilZam`
    * `crue10.modele.Modele` :
        * [MAJEUR] la méthode `get_branches_liste_entre_noeuds` devient `get_liste_branches_entre_deux_noeuds`
    * `crue10.run` :
        * [MAJEUR] la méthode `get_results` devient `get_resultats_calcul` (en prévision de l'ajout des résultats du pré-traitement géométrique)
    * `crue10.run.results` devient `crue10.run.resultats_calcul` :
        * la classe `RunResults` devient `ResultatsCalcul`
        * [MAJEUR] la méthode `get_res_steady` devient `get_data_pseudoperm`
        * [MAJEUR] la méthode `get_res_unsteady` devient `get_data_trans`
        * Pour les métadonnées des calculs :
            * [MAJEUR] l'attribut `calc_steady_dict` devient `res_calc_pseudoperm`
            * [MAJEUR] l'attribut `calc_unsteady_dict` devient `res_calc_trans`
            * la méthode `get_calc_steady` devient `get_res_calc_pseudoperm`
            * la méthode `get_calc_unsteady` devient `get_res_calc_trans`
            * la méthode `CalcPseudoPerm` devient `ResCalcPseudoPerm` (pour éviter le conflit avec `crue10.scenario.calcul`)
            * la méthode `CalcTrans` devient `ResCalcTrans` (pour éviter le conflit avec `crue10.scenario.calcul`)
        * Pour les post-traitements : 
            * [MAJEUR] la méthode `get_res_all_steady_var_at_emhs` devient `get_all_pseudoperm_var_at_emhs_as_array`
            * [MAJEUR] la méthode `get_res_unsteady_var_at_emhs` devient `get_trans_var_at_emhs_as_array`
            * [MAJEUR] la méthode `export_calc_steady_as_csv` devient `write_all_calc_pseudoperm_in_csv`
            * [MAJEUR] la méthode `export_calc_steady_as_csv` devient `write_all_calc_trans_in_csv`
            * [MAJEUR] la méthode `get_res_steady_at_sections_along_branches_as_dataframe` devient `extract_profil_long_pseudoperm_as_dataframe`
            * [MAJEUR] la méthode `get_res_unsteady_at_sections_along_branches_as_dataframe` devient `extract_profil_long_trans_at_time_as_dataframe`
            * [MAJEUR] la méthode `get_res_unsteady_max_at_sections_along_branches_as_dataframe` devient `extract_profil_long_trans_max_as_dataframe`
            * [MAJEUR] la méthode `export_calc_unsteady_as_df` devient `extract_res_trans_as_dataframe`
            * [MAJEUR] la méthode `export_calc_unsteady_as_csv_table` est supprimée
    * `crue10.scenario.Scenario` :
        * [MAJEUR] la méthode `get_last_run` devient `get_dernier_run`
        * la méthode `add_run` devient `ajouter_run`
        * l'attribut `current_run_id` devient `nom_run_courant`
        * la méthode `set_current_run_id` devient `set_run_courant`
        * la méthode `get_liste_run_ids` devient `get_liste_noms_runs`

### Corrections
- `crue10.etude.Etude._read_etu` : génère une exception `ExceptionCrue10` au lieu d'une `PermissionError`
    s'il s'agit d'un dossier
- `crue10.emh.casier.ProfilCasier` : ajout propriété `xz_filtered` et utilisation pour `compute_surface`
    (pour considérer seulement le lit utile)

## [3.1] - 2022-07-21
Version avant préparation pour ajout nouvelle grammaire v1.3

## [3.0] - 2022-03-02
Grammaire v1.2 et support POC MEC Latest

## [2.0] - 2020-01-10
Major refactoring done and full support of Python>=2.6

## [1.0] - 2020-01-09
Refactoring with more french and closer to cpp
