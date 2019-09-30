Crue10 tools
============

> Outil pour manipuler des modèles 1D au format `Crue10` (code de calcul, propriétée de CNR).

## Crue10 API - Parseur de fichiers

- Lecture d'une étude et la géométrie
  - [Lire une étude](snippets/read_studies.py)
  - [Lire un modèle](snippets/read_model.py)
  - [Lire un sous-modèle et ses EMHs](snippets/read_submodel.py)
- Écriture d'une étude et la géométrie
  - [Écrire un sous-modèle](snippets/write_submodel_from_scratch.py)
  - [Écrire une étude](snippets/write_study_from_scratch.py)
- Calcul (= lancer un run)
    - [Créer et lancer une série de runs](snippets/run_calculations.py)
- Post-traitement de résultats (d'un run)
  - [Lire un run avec ses résultats](snippets/read_run_and_results.py)
  - [Lire un modèle et les résultats d'un run associé](snippets/read_model_and_run.py)

## Scripts en ligne de commande

Voir [wiki pages](https://github.com/CNR-Engineering/Crue10_tools/wiki) pour savoir comment utiliser ces outils.
