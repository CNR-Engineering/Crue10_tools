"""
Étude fictive représentant l'équivalent de 30 km de Rhône (par VRH>RET>CAA) répartis comme suit :

| Zone | Longueur | Début PK |  Fin PK |
|------|----------|----------|---------|
| VRH  | 10 km    |   80.000 |  90.000 |
| CAF  | 3 km     |   87.000 |  90.000 |
| RET  | 15 km    |   90.000 | 105.000 |
| AMB  | 500 m    |  105.000 | 105.500 |
| BAR  | 500 m    |  105.500 | 106.000 |
| AVB  | 200 m    |  106.000 | 106.200 |
| CAA  | 5 km     |  105.000 | 110.000 |
| AFF  | 6 km     |        - | 100.500 |
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

from snippets.construire_et_ecrire_sous_modele import smfs_amont, smfs_cas, smfs_caa, smfs_bgefileau, smfs_bgegenerique


def creer_etude_from_scratch(etu_path):
    """
    Écrire une étude fictive complète à partir d'objets Crue10_tools uniquement
    """
    etude_out = Etude(etu_path, metadata=DEFAULT_METADATA,
                      comment="Etude fictive from scratch", mode='w')

    # Sc_multi_avec_bgefileau
    mo_multi_avec_bgefileau = Modele('Mo_multi_avec_bgefileau', metadata=DEFAULT_METADATA, mode='w')
    mo_multi_avec_bgefileau.ajouter_liste_sous_modeles([
        smfs_amont.sous_modele,
        smfs_cas.sous_modele,
        smfs_caa.sous_modele,
        smfs_bgefileau.sous_modele,
    ])

    sc_multi_avec_bgefileau = Scenario('Sc_multi_avec_bgefileau', mo_multi_avec_bgefileau, metadata=DEFAULT_METADATA, mode='w')
    etude_out.ajouter_scenario(sc_multi_avec_bgefileau)

    # Sc_multi_avec_bgegenerique
    mo_multi_avec_bgegenerique = Modele('Mo_multi_avec_bgegenerique', metadata=DEFAULT_METADATA, mode='w')
    mo_multi_avec_bgegenerique.ajouter_liste_sous_modeles([
        smfs_amont.sous_modele,
        smfs_cas.sous_modele,
        smfs_caa.sous_modele,
        smfs_bgegenerique.sous_modele,
    ])
    sc_multi_avec_bgegenerique = Scenario('Sc_multi_avec_bgegenerique', mo_multi_avec_bgegenerique, metadata=DEFAULT_METADATA, mode='w')
    etude_out.ajouter_scenario(sc_multi_avec_bgegenerique)

    # Sc_mono_sm
    sm_mono_sm = SousModele('Sm_mono_sm', metadata=DEFAULT_METADATA, mode='w')
    sm_mono_sm.ajouter_emh_depuis_sous_modele(smfs_amont.sous_modele)
    sm_mono_sm.ajouter_emh_depuis_sous_modele(smfs_cas.sous_modele)
    sm_mono_sm.ajouter_emh_depuis_sous_modele(smfs_caa.sous_modele)
    sm_mono_sm.ajouter_emh_depuis_sous_modele(smfs_bgefileau.sous_modele)
    sm_mono_sm.set_comment(sm_mono_sm.summary())

    mo_mono_sm = Modele('Mo_mono_sm', metadata=DEFAULT_METADATA, mode='w')
    mo_mono_sm.ajouter_sous_modele(sm_mono_sm)

    sc_mono_sm = Scenario('Sc_mono_sm', mo_mono_sm, metadata=DEFAULT_METADATA, mode='w')
    etude_out.ajouter_scenario(sc_mono_sm)

    # Reset initial conditions
    mo_multi_avec_bgefileau.reset_initial_conditions()
    mo_multi_avec_bgegenerique.reset_initial_conditions()
    mo_mono_sm.reset_initial_conditions()

    # Set comments
    mo_multi_avec_bgefileau.set_comment(mo_multi_avec_bgefileau.summary())
    mo_multi_avec_bgegenerique.set_comment(mo_multi_avec_bgegenerique.summary())
    mo_mono_sm.set_comment(mo_mono_sm.summary())

    sc_multi_avec_bgefileau.set_comment(sc_multi_avec_bgefileau.summary())
    sc_multi_avec_bgegenerique.set_comment(sc_multi_avec_bgefileau.summary())
    sc_mono_sm.set_comment(sc_mono_sm.summary())

    etude_out.nom_scenario_courant = sc_mono_sm.id
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
            etu_folder = etude_in.folder
            path_svg = os.path.join(etu_folder, f"graphe_{modele.id}.svg")
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
