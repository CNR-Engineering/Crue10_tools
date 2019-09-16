"""
Lancement d'un calcul Crue10:
1) Création d'un nouveau run (sans mettre à jour le fichier etu.xml en entrée)
2) Ecriture des fichiers XML dans un nouveau dossier du run
2) Lancement de crue10.exe en ligne de commande

Même comportement que Fudaa-Crue :
- Dans le fichier etu.xml:
    - on conserve la liste des Runs précédents (sans copier les fichiers)
    - on conserve les Sm/Mo/Sc qui sont hors du Sc courant
- Seuls les XML du scénario courant sont écrits dans le dossier du run
- Les XML du modèle associés sont écrits dans un sous-dossier
- Les données géographiques (fichiers shp) des sous-modèles ne sont pas copiées

TODO: Copier proprement les fichiers du modèle/scénario sans utiliser le template!
"""
from crue10.study import Study


study = Study('../crue10_examples/Etudes-tests/Etu_BE2016_conc/Etu_BE2016_conc.etu.xml')
study.read_all()

scenario = study.get_scenario('Sc_BE2016_etatref')

exit_code = scenario.create_and_launch_new_run(study)
print(exit_code)
