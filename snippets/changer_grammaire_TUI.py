import logging
from glob import glob
import os
import shutil

from crue10.etude import Etude
from crue10.sous_modele import SousModele
from crue10.utils import ExceptionCrue10, logger


logger.setLevel(logging.ERROR)

dry = True
if dry:
    FOLDER_IN = 'C:/PROJETS/SHY_C10_Crue10_Source/tests/RUNS'
    FOLDER_OUT = 'C:/PROJETS/SHY_C10_Crue10_Source/tests/RUNS_g1.3'
else:
    FOLDER_IN = 'C:/PROJETS/SHY_C10_Crue10_Source/tests/RUNS_g1.2'
    FOLDER_OUT = 'C:/PROJETS/SHY_C10_Crue10_Source/tests/RUNS'.replace('/', os.sep)


# shutil.rmtree(FOLDER_OUT)

for etu_path_in in glob(os.path.join(FOLDER_IN, '**', '*.etu.xml'), recursive=True):
    logger.info(etu_path_in)
    etude = Etude(etu_path_in)
    scenario = etude.get_scenario_courant()
    # etude.ignore_others_scenarios(scenario.id)

    mo_folders = glob(os.path.join(os.path.dirname(etu_path_in), 'Mo_*'))
    if len(mo_folders) == 0:
        raise RuntimeError
    elif len(mo_folders) > 1:
        if 'Sc_M3-6_TestEMHinactives_c10' not in etu_path_in:
            logger.critical("Plusieurs dossiers Mo_: %s, %i, %s" % (etu_path_in, len(mo_folders), mo_folders))
            continue

    # Add subfolder for all SousModele files
    for sous_modele in etude.get_liste_sous_modeles():
        to_delete = False
        for xml_type, file_path in sous_modele.files.items():
            if xml_type in SousModele.FILES_XML:
                folder, basename = os.path.dirname(file_path), os.path.basename(file_path)
                new_file_path = os.path.join(folder, scenario.modele.id, basename)
                sous_modele.files[xml_type] = new_file_path
                if not os.path.exists(new_file_path):
                    to_delete = True
        if to_delete:
            etude.supprimer_sous_modele(sous_modele.id)

    # Add subfolder for all Modele files
    modele = scenario.modele
    for mo in etude.get_liste_modeles():
        if mo.id != modele.id:
            etude.supprimer_modele(mo.id)
        else:
            for xml_type, file_path in modele.files.items():
                folder, basename = os.path.dirname(file_path), os.path.basename(file_path)
                new_file_path = os.path.join(folder, modele.id, basename)
                modele.files[xml_type] = new_file_path

        # to_delete = False
        # for xml_type, file_path in modele.files.items():
        #     folder, basename = os.path.dirname(file_path), os.path.basename(file_path)
        #     new_file_path = os.path.join(folder, modele.id, basename)
        #     modele.files[xml_type] = new_file_path
        #     if not os.path.exists(new_file_path):
        #         to_delete = True
        # if to_delete:
        #     etude.supprimer_modele(modele.id)

    for sc in etude.get_liste_scenarios():
        if sc.id != scenario.id:
            etude.supprimer_scenario(sc.id)

    etude.reset_filename_list()  # useful because of previous modifications
    for file_path in etude.filename_list:
        if not os.path.exists(file_path):
            raise ExceptionCrue10("Fichier introuvable: %s" % file_path)

    try:
        etude.read_all()
        # etude.log_check_xml(folder=os.path.dirname(etu_path_in))
        # etude.changer_version_grammaire('1.3')
    except ExceptionCrue10 as e:
        logger.error("ERROR: %s" % e)
        continue

    # etu_path_out = etu_path_in.replace(FOLDER_IN, FOLDER_OUT)
    # etu_folder = os.path.dirname(etu_path_out)
    # mo_folder = os.path.join(etu_folder, modele.id)
    # etude.move(etu_folder)
    #
    # scenario.write_all(etu_folder, folder_config=None, write_model=False)
    # modele.write_all(mo_folder, folder_config=None)
    # etude.write_etu()
