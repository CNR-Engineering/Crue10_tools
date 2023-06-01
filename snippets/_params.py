# coding: utf-8
"""
Les versions des différents exécutables Crue10 :
* 'qualif_c10m9': '10.1.12'
* 'prod': '10.2.0'
* 'local_v10.2': '10.2.0'  # Branche v10.2 créée le 04/07/2017 (source non précisé)
* 'qualif_old_c10m10': '10.2.0'
* 'qualif_c10m10v111': '10.3.0'
* 'qualif': '10.3.2'  # Branche v10.3 (VS2017) créée le 20/03/2018 (à partir de v10.3)
* 'local_v10.3': '10.3.2'  # Branche v10.3 créée le 25/01/2018 (à partir de DEV)
"""
from collections import OrderedDict
from os import sep

from crue10.utils import logger


CSV_DELIMITER = ';'


CRUE10_EXE_REFERENCE = 'prod'


CRUE10_EXE = OrderedDict([
    # Liste des exécutables Crue10 à comparer
    ('prod', 'P:/FudaaCrue/etc/coeurs/c10m10/exe/crue10.exe'.replace('/', sep)),
    ('qualif', 'Q:/Qualif_Exec/FudaaCrue/etc/coeurs/c10m10/exe/crue10.exe'.replace('/', sep)),

    # Référence utilisée pour les calculs de différences
    # ('prod', 'P:/FudaaCrue/etc/coeurs/c10m10/exe/crue10.exe'.replace('/', sep)),

    # Calculs à comparer à la référence
    # failed .STO/.STR missing: ('qualif_c10m9', 'Q:/Qualif_Exec/FudaaCrue/etc/coeurs/c10m9/exe/crue10.exe'.replace('/', sep)),
    # same as prod: ('qualif_old_c10m10', 'Q:/Qualif_Exec/FudaaCrue/etc/coeurs/old_c10m10/exe/crue10.exe'.replace('/', sep)),
    # ('qualif_c10m10v111', 'Q:/Qualif_Exec/FudaaCrue/etc/coeurs/c10m10v111/exe/crue10.exe'.replace('/', os.sep)),
    # ('qualif', 'Q:/Qualif_Exec/FudaaCrue/etc/coeurs/c10m10/exe/crue10.exe'.replace('/', sep)),
])


ETATREF_SCENARIO_PAR_AMENAGEMENT = OrderedDict([
    # Scénario à utiliser par aménagement s'il diffère du "scénario courant" (sinon mettre `None`)
    # DTHR
    ('Etu_GE2017_Conc', 'Sc_Calperm_GE_QRef_br14'),
    ('Etu_SY2016_Conc', 'Sc_etats_ref'),
    ('Etu_CE2016_Conc', 'Sc_CE2016_EtatsRef_Qres50'),
    ('Etu_BY2018_Conc', 'Sc_BY20_Conc'),
    ('Etu_BC2020_Conc', 'Sc_BC2020_Etats_ref'),
    ('Etu_SB2013_Conc', 'Sc_SB2013_c9c9c10'),

    # DTRI
    ('Etu_PB2017_Conc', 'Sc_PB_Etats_ref'),
    ('Etu_VS2015_conc', 'Sc_EtatsRef2015'),
    ('Etu_PR2019_Conc', 'Sc_PR2019_Conc'),
    ('Etu_SV2019_Conc', 'Sc_SV2019_Conc_EtatRef'),

    # DTRS
    ('Etu_BV2016_Conc_Etatref - ISfonds2016_K2016', 'Sc_BV2016_Conc__TLC'),
    ('Etu_BE2016_conc', 'Sc_BE2016_etatref'),
    ('Etu_LN2013_Conc', 'Sc_LN2013_EtatRef'),
    ('Etu_MO2018_Conc', 'Sc_MO2018_Conc'),

    # DTRM
    ('Etu_DM2018_Conc', 'Sc_DM2018_Conc_Etats_ref'),
    ('Etu_CA2020_Conc', 'Sc_CA2020_Conc'),
    ('Etu_AV2020_Conc', 'Sc_AV2020_Etats_Ref'),
    ('Etu_VA2018_Conc', 'Sc_Etat_REF_VA_conc_2018'),
    ('Etu_avaVA2018_Conc', 'Sc_ETAT_REF'),
])
# Filtre sur les aménagements voulus
# ETATREF_SCENARIO_PAR_AMENAGEMENT = {etude_dossier: ETATREF_SCENARIO_PAR_AMENAGEMENT[etude_dossier]
#                                     for etude_dossier in ['Etu_GE2017_Conc', 'Etu_SY2016_Conc']}


def write_csv(dataframe, file_path):
    logger.info("Writing %s (shape=%s)" % (file_path, dataframe.shape))
    dataframe.to_csv(file_path, sep=CSV_DELIMITER, index=False)
