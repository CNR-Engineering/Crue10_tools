"""
Étude fictive d'un bief nommé XX représentant l'équivalent de 30 km sur le Bas-Rhône (par VRH>RET>CAA) répartis comme suit :

| Zone | Longueur | Début PK Rhône |  Fin PK Rhône | Sous-modèle unitaire    |
|------|----------|----------------|---------------|-------------------------|
| VRH  | 10 km    |         80.000 |        90.000 | Sm_amont_min            |
| CAF  | 3 km     |         87.000 |        90.000 | Sm_amont_min            |
| RET  | 15 km    |         90.000 |       105.000 | Sm_amont_min / Sm_bge*  |
| AMB  | 600 m    |        105.000 |       105.600 | Sm_bge*                 |
| BAR  | 400 m    |        105.600 |       106.000 | Sm_bge*                 |
| AVB  | 20 m     |        106.000 |       106.020 | Sm_bge*                 |
| CAA  | 5 km     |        105.000 |       110.000 | Sm_canal_amenee         |
| AFF  | 6 km     |              - |       100.500 | Sm_amont_min            |
| CCA  | -        |              - |             - | Sm_plaine               |
| CCB  | -        |              - |             - | Sm_plaine               |

Les scénarios Sc_mono_sm_avec_bgefileau et Sc_multi_sm_avec_bgefileau comportent les mêmes EMHs mais réparties
soit dans un unique sous-modèle (Sm_mono_sm_avec_bgefileau), soit dans 4 sous-modèles différents (pour ce second scénario).

Quelques remarques :
- La branche barrage fait 400m (couvre 100m en amont + 300m en aval)
- La plaine est découpée en 2 zones : CCA et CCB
"""
import logging
import os.path

from crue10.etude import Etude
from crue10.modele import Modele
from crue10.sous_modele import SousModele
from crue10.scenario import Scenario
from crue10.tests import DATA_TESTS_FOLDER_ABSPATH, DEFAULT_METADATA
from crue10.utils import ExceptionCrue10, get_file_docstring, logger
from crue10.utils.settings import VERSION_GRAMMAIRE_COURANTE, VERSION_GRAMMAIRE_PRECEDENTE

from snippets.construire_et_ecrire_sous_modele import smfs_amont_min, smfs_plaine, smfs_canal_amenee, smfs_bgefileau, smfs_bgegen


def creer_etude_from_scratch(etu_path):
    """
    Écrire une étude fictive complète à partir d'objets Crue10_tools uniquement
    """
    etude_out = Etude(etu_path, metadata=DEFAULT_METADATA,
                      comment="Etude fictive from scratch", mode='w')

    # Sc_multi_sm_avec_bgefileau
    mo_multi_sm_avec_bgefileau = Modele('Mo_multi_sm_avec_bgefileau', metadata=DEFAULT_METADATA, mode='w')
    mo_multi_sm_avec_bgefileau.ajouter_liste_sous_modeles([
        smfs_amont_min.sous_modele,
        smfs_plaine.sous_modele,
        smfs_canal_amenee.sous_modele,
        smfs_bgefileau.sous_modele,
    ])

    sc_multi_sm_avec_bgefileau = Scenario('Sc_multi_sm_avec_bgefileau', mo_multi_sm_avec_bgefileau, metadata=DEFAULT_METADATA, mode='w')
    etude_out.ajouter_scenario(sc_multi_sm_avec_bgefileau)

    # Sc_multi_sm_avec_bgegen
    mo_multi_sm_avec_bgegen = Modele('Mo_multi_sm_avec_bgegen', metadata=DEFAULT_METADATA, mode='w')
    mo_multi_sm_avec_bgegen.ajouter_liste_sous_modeles([
        smfs_amont_min.sous_modele,
        smfs_plaine.sous_modele,
        smfs_canal_amenee.sous_modele,
        smfs_bgegen.sous_modele,
    ])
    sc_multi_sm_avec_bgegen = Scenario('Sc_multi_sm_avec_bgegen', mo_multi_sm_avec_bgegen, metadata=DEFAULT_METADATA, mode='w')
    etude_out.ajouter_scenario(sc_multi_sm_avec_bgegen)

    # Sc_mono_sm
    sm_mono_sm_avec_bgefileau = SousModele('Sm_mono_sm_avec_bgefileau', metadata=DEFAULT_METADATA, mode='w')
    sm_mono_sm_avec_bgefileau.ajouter_emh_depuis_sous_modele(smfs_amont_min.sous_modele)
    sm_mono_sm_avec_bgefileau.ajouter_emh_depuis_sous_modele(smfs_plaine.sous_modele)
    sm_mono_sm_avec_bgefileau.ajouter_emh_depuis_sous_modele(smfs_canal_amenee.sous_modele)
    sm_mono_sm_avec_bgefileau.ajouter_emh_depuis_sous_modele(smfs_bgefileau.sous_modele)
    sm_mono_sm_avec_bgefileau.set_comment(sm_mono_sm_avec_bgefileau.summary())

    mo_mono_sm_avec_bgefileau = Modele('Mo_mono_sm_avec_bgefileau', metadata=DEFAULT_METADATA, mode='w')
    mo_mono_sm_avec_bgefileau.ajouter_sous_modele(sm_mono_sm_avec_bgefileau)

    sc_mono_sm_avec_bgefileau = Scenario('Sc_mono_sm_avec_bgefileau', mo_mono_sm_avec_bgefileau, metadata=DEFAULT_METADATA, mode='w')
    etude_out.ajouter_scenario(sc_mono_sm_avec_bgefileau)

    # Reset initial conditions
    mo_multi_sm_avec_bgefileau.reset_initial_conditions()
    mo_multi_sm_avec_bgegen.reset_initial_conditions()
    mo_mono_sm_avec_bgefileau.reset_initial_conditions()

    # Set comments
    mo_multi_sm_avec_bgefileau.set_comment(mo_multi_sm_avec_bgefileau.summary())
    mo_multi_sm_avec_bgegen.set_comment(mo_multi_sm_avec_bgegen.summary())
    mo_mono_sm_avec_bgefileau.set_comment(mo_mono_sm_avec_bgefileau.summary())

    sc_multi_sm_avec_bgefileau.set_comment(sc_multi_sm_avec_bgefileau.summary())
    sc_multi_sm_avec_bgegen.set_comment(sc_multi_sm_avec_bgefileau.summary())
    sc_mono_sm_avec_bgefileau.set_comment(sc_mono_sm_avec_bgefileau.summary())

    etude_out.nom_scenario_courant = sc_mono_sm_avec_bgefileau.id
    etude_out.set_comment(etude_out.summary() + "\n\n" + etude_out.details() + "\n\n" + get_file_docstring(__file__))

    return etude_out


if __name__ == "__main__":
    logger.setLevel(logging.INFO)

    for version_grammaire in [VERSION_GRAMMAIRE_COURANTE, VERSION_GRAMMAIRE_PRECEDENTE]:  # Order is important
        etu_path = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', version_grammaire, 'Etu_from_scratch',
                                'Etu_from_scratch.etu.xml')
        etude_out = creer_etude_from_scratch(etu_path)
        if version_grammaire != etude_out.version_grammaire:
            etude_out.changer_version_grammaire(version_grammaire=version_grammaire)

        etude_out.write_all()

        # Read this new Etude to check its integrity
        etude_in = Etude(etu_path, mode='r')
        try:
            etude_in.read_all()
        except ExceptionCrue10 as e:
            logger.critical("Exception à l'ouverture de l'étude:\n%s" % e)

        # Write topographical graphs
        def write_topographical_graph(modele):
            folder = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'graphes_topographiques', 'Etu_from_scratch')
            path_svg = os.path.join(folder, f"{modele.id}.svg")
            modele.write_topological_graph([path_svg])
        if version_grammaire == VERSION_GRAMMAIRE_COURANTE:
            for modele in etude_in.get_liste_modeles():
                write_topographical_graph(modele)

        logger.info('-' * 32 + '\nVérification ré-ouverture étude:')
        logger.info(etude_in.summary())
        etude_in.log_check_xml()
        for scenario in etude_in.get_liste_scenarios():
            logger.info(f"Check XML sur {scenario.id}@{etu_path}")
            scenario.log_check_xml_scenario(os.path.dirname(etu_path))
