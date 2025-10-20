"""
Écrire une étude fictive complète à partir d'objets Crue10_tools uniquement

Pour plus de détails, voir également le graphe topologique (fichier `graphe_Mo_mono_sm.svg`)
"""
import logging
import os.path

from crue10.etude import Etude
from crue10.utils import ExceptionCrue10, logger
from crue10.utils.settings import VERSION_GRAMMAIRE_COURANTE, VERSION_GRAMMAIRE_PRECEDENTE
from crue10.tests import DATA_TESTS_FOLDER_ABSPATH, DEFAULT_METADATA


def validate_and_write_etude_from_scratch(etu_path, version_grammaire):
    # Prepare an empty Etude
    etude_out = Etude(etu_path, metadata=DEFAULT_METADATA, version_grammaire=version_grammaire,
                      comment="Etude fictive from scratch", mode='w')
    etude_out.create_empty_scenario('Sc_mono_sm', 'Mo_mono_sm', 'Sm_mono_sm',
                                    metadata=DEFAULT_METADATA)
    scenario_out = etude_out.get_scenario('Sc_mono_sm')
    scenario_out.metadata['Commentaire'] = scenario_out.summary()
    modele_out = etude_out.get_modele('Mo_mono_sm')
    modele_out.metadata['Commentaire'] = modele_out.summary()
    sous_modele_out = etude_out.get_sous_modele('Sm_mono_sm')

    if True:
        # Add some EMHs in sous_modele_out
        from snippets.construire_et_ecrire_sous_modele import sous_modele
        if version_grammaire != sous_modele.version_grammaire:
            sous_modele.changer_version_grammaire(version_grammaire=version_grammaire)

        sous_modele_out.metadata['Commentaire'] = sous_modele.metadata['Commentaire']
        sous_modele_out.ajouter_emh_depuis_sous_modele(sous_modele)

    etude_out.metadata['Commentaire'] = etude_out.summary()

    logger.debug(etude_out.summary())
    logger.debug(etude_out.get_sous_modele('Sm_mono_sm').summary())

    modele_out.reset_initial_conditions()
    # modele_out.write_topological_graph([os.path.join('out', 'Etu_mono_sm', 'graphe_Mo_mono_sm.svg')])

    logger.debug('-' * 32 + '\nValidation sous-modèle:')
    sous_modele_out.log_validation()
    etude_out.write_all()
    return etude_out


if __name__ == "__main__":
    logger.setLevel(logging.INFO)

    for version_grammaire in [VERSION_GRAMMAIRE_COURANTE, VERSION_GRAMMAIRE_PRECEDENTE]:
        etu_path = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', version_grammaire, 'Etu_from_scratch',
                                'Etu_from_scratch.etu.xml')
        validate_and_write_etude_from_scratch(etu_path, version_grammaire)

        # Read this new Etude to check its integrity
        etude_in = Etude(etu_path, mode='r')
        try:
            etude_in.read_all()
        except ExceptionCrue10 as e:
            logger.critical("Exception à l'ouverture de l'étude:\n%s" % e)

        logger.debug('-' * 32 + '\nVérification ré-ouverture étude:')
        logger.debug(etude_in.summary())
        logger.debug(etude_in.get_sous_modele('Sm_mono_sm').summary())
        etude_in.log_check_xml()
