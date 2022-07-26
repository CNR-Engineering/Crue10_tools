Journal des modifications
=========================

## [4.0] - yyyy-mm-dd

### Added
- Support en lecture/écriture des grammaires v1.2 et v1.3 :
    * Ajout de 2 variables utilisateurs : `VERSION_GRAMMAIRE_PRECEDENTE` et `VERSION_GRAMMAIRE_COURANTE`
    * [MAJOR] `crue10.emh.branche.BrancheBarrageFilEau`: attribut `liste_elements_seuil` se nomme maintenant
        `liste_elements_barrage`

Détails :
* Les grammaires doivent être identiques en lecture pour chaque Etude/Scenario/Modele/SousModele (plantage sinon)

### Changed
- Refactoring :
    * `crue10.base`: la classe `FichierXML` devient `EnsembleFichiersXML`, son attribut `access` devient `mode`
        (par héritage, l'attribut change aussi pour `Etude`, `Scenario`, `Modele`, `SousModele`, `FichierOtfa`)
    * `crue10.scenario.Scenario`: la méthode `get_branches_liste_entre_noeuds` devient `get_liste_branches_entre_noeuds`

### Fixed
- `etude.Etude._read_etu`: génère une exception `ExceptionCrue10` au lieu d'une `PermissionError` s'il s'agit d'un
    dossier

## [3.1] - 2022-07-21
Version avant préparation pour ajout nouvelle grammaire v1.3

## [3.0] - 2022-03-02
Grammaire v1.2 et support POC MEC Latest

## [2.0] - 2020-01-10
Major refactoring done and full support of Python>=2.6

## [1.0] - 2020-01-09
Refactoring with more french and closer to cpp