Crue10 tools
============

![Python package](https://github.com/CNR-Engineering/Crue10_tools/workflows/Python%20package/badge.svg)

Versions Python testées : 2.7, 3.5, 3.6 et 3.7.

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
  - [Créer et lancer une série de runs](snippets/run_calculations.py)
- Post-traitement de résultats (d'un run)
  - [Lire un run avec ses résultats](snippets/lire_run_et_resultats.py)
  - [Lire un modèle et les résultats d'un run associé](snippets/lire_modele_et_run.py)

## Scripts en ligne de commande

Voir [les pages wiki](https://github.com/CNR-Engineering/Crue10_tools/wiki) pour savoir comment utiliser ces outils.
