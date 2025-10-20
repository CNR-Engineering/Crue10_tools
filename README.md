Crue10 tools
============

[![Python package](https://github.com/CNR-Engineering/Crue10_tools/workflows/Python%20package/badge.svg)](https://github.com/CNR-Engineering/Crue10_tools/actions)
[![Documentation Status](https://readthedocs.org/projects/crue10-tools/badge/?version=latest)](https://crue10-tools.readthedocs.io/fr/latest/)

Versions Python compatibles : 3.10, 3.11 3.12 et 3.13.

> Outil pour manipuler des modèles 1D au format `Crue10` (code de calcul, propriétée de CNR).

## Crue10 API - Parseur de fichiers

- Lecture d'une étude et la géométrie
  - [Lire une étude](snippets/lire_etudes.py)
  - [Lire un modèle](snippets/lire_modele.py)
  - [Lire un sous-modèle et ses EMHs](snippets/lire_sous_modele.py)
- Écriture d'une étude et la géométrie
  - [Écrire un sous-modèle](snippets/construire_et_ecrire_sous_modele.py)
  - [Écrire une étude](snippets/ecrire_etude.py)
- Calcul (= lancer un run)
  - [Créer et lancer un run](snippets/run_single_calculation.py)
  - [Créer et lancer une série de runs en parallèle](snippets/run_parallel_calculations.py)
- Post-traitement de résultats (d'un run)
  - [Lire un run avec ses résultats](snippets/lire_run_et_resultats.py)
  - [Lire un modèle et les résultats d'un run associé](snippets/lire_modele_et_run.py)

## Scripts en ligne de commande

Voir [les pages wiki](https://github.com/CNR-Engineering/Crue10_tools/wiki) pour savoir comment utiliser ces outils.

## Tests unitaires

Le lancement de tous les tests unitaires (présents dans `crue10/tests`) se fait avec la commande :

```
python -m unittest
````

Un test spécifique peut être lancé avec une commande du type :

```
python -m unittest crue10.tests.test_end_to_end.EndToEndTestCase.test_write_gcour_from_scratch
```

Liste des tests unitaires par classes principales :
* Etude => `test_end_to_end.py`, `test_file_xsd_validation.py`
* Scenario => `test_scenario.py`
* Modele => `test_modele.py`
* SousModele => `test_sous_modele.py`
* EMH
    * branches => `test_emh_branche.py`
    * casiers => `test_emh_casier.py`  
    * noeuds => `test_emh_noeud.py`
    * sections => `test_emh_section.py`
* Run => `test_run.py`
* ResultatsCalcul => `test_resultats_calcul_gprec.py`, `test_resultats_calcul_gcour.py`
* utils :
    * CrueConfigMetier => `test_crueconfigmetier.py`
    * timer => `test_timer.py`
    * traceback => `test_traceback.py`

Les tests unitaires sont vérifiés à chaque push grâce à un workflow Github et peuvent être déclenchés manuellement si
besoin. La coche verte ou la croix rouge à côté du commit permet de savoir rapidement s'ils se sont bien passés.
