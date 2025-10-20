"""
Sous-modèle unique avec les 8 zones distinctes (sans compter BGE)

30 km fictif de Rhône (par VRH>RET>CAA) répartis comme suit :

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
from math import ceil, floor
import numpy as np
import os.path
import re
from shapely.affinity import translate
from shapely.geometry import Point, LinearRing

from crue10.emh.branche import Branche, BranchePdC, BrancheSeuilTransversal, \
    BrancheSeuilLateral, BrancheOrifice, BrancheStrickler, BrancheNiveauxAssocies, \
    BrancheBarrageGenerique, BrancheBarrageFilEau, BrancheSaintVenant
from crue10.emh.casier import Casier, ProfilCasier
from crue10.emh.noeud import Noeud
from crue10.emh.section import LimiteGeom, SectionIdem, SectionProfil, SectionSansGeometrie
from crue10.sous_modele import SousModele
from crue10.utils import ExceptionCrue10, get_file_docstring, logger


TRIGRAMME_AFFLUENT = 'AFF'
TRIGRAMME_PLAINE = 'CAS'
TRIGRAMME_RETENUE = 'RET'
TRIGRAMME_VIEUX_RHONE = 'VRH'

PKM_RESTITUTION = 90000
PKM_DEBUT_PLAINE = 96000
PKM_CONFLUENCE_AFFLUENT = 100500
PKM_DIFFLUENCE = 105000

DELTA_XP_BATHY = {  # Distances entre 2 profils Bathy en mètres
    TRIGRAMME_AFFLUENT: 1000,
    TRIGRAMME_RETENUE: 200,
    TRIGRAMME_VIEUX_RHONE: 400,
    'CAA': 250,
    'CAF': 500,
}

X_CENTERED_VALUE = 800000  # Pour que ça ressemble à une abscisse en Lambert 93 sur le Rhône
Y_OFFSET = 6400000  # Pour que ça ressemble à une ordonnées en Lambert 93 sur le Rhône

DISTANCE_CASIER = 2000
TAILLE_CASIER = 1800

LETTERS_FOR_SECTIONIDEM = ['a', 'b', 'c']


# Define helpers
def pk_km_to_pkm(pk_km):
    return 1000 * float(pk_km)


def pkm_to_pk_km(pkm):
    return "{:,.0f}".format(pkm).replace(',', '.')


def pkm_to_y_position(pk):
    return Y_OFFSET - pk


def get_trigramme_and_pk_km(nom_emh):
    """Retourne le trigramme et le PK à partir du nom de l'EMH"""
    if f'_{TRIGRAMME_RETENUE}' in nom_emh[3:]:
        match = re.match(r'^(Br|Nd|St)_(?P<trigramme>[A-Z]{3})(?P<pk_km>[0-9.]+)_(?P<trigramme_av>[A-Z]{3})(?P<complement>[\w]*?)$', nom_emh)
    elif '-' in nom_emh:
        match = re.match(r'^(Br|Nd|St)_(?P<trigramme>[A-Z]{3})(?P<pk_km>[0-9.]+)-(?P<pk_km_av>[0-9.]+)(?P<complement>[\w]*?)$', nom_emh)
    else:
        match = re.match(r'^(Br|Nd|St)_(?P<trigramme>[A-Z]{3})(?P<pk_km>[0-9.]+)(?P<complement>[\w]*?)$', nom_emh)
    return match.group('trigramme'), match.group('pk_km')


# Build a SousModele
sous_modele = SousModele('Sm_mono_sm', mode='w')
sous_modele.ajouter_lois_frottement_par_defaut()


def ajouter_noeud(nom_noeud):
    trigramme, pk_km = get_trigramme_and_pk_km(nom_noeud)
    pkm = pk_km_to_pkm(pk_km)

    noeud = Noeud(nom_noeud)

    x_position = X_CENTERED_VALUE
    if trigramme == TRIGRAMME_VIEUX_RHONE:
        x_position -= (PKM_RESTITUTION - pkm) / 5
    elif trigramme == 'CAF':
        x_position += 3000
    elif trigramme == 'AMB' or trigramme == 'AVB':
        x_position -= (pkm - PKM_DIFFLUENCE) / 2
    elif trigramme == 'CAA':
        x_position += (pkm - PKM_DIFFLUENCE) / 5
    elif trigramme == TRIGRAMME_AFFLUENT:
        x_position += pkm
    elif trigramme == TRIGRAMME_PLAINE:
        x_position -= 1500

    if trigramme == TRIGRAMME_AFFLUENT:
        y_position = pkm_to_y_position(PKM_CONFLUENCE_AFFLUENT)
    elif trigramme == TRIGRAMME_PLAINE:  # CAS1 sera à PKM_DEBUT_PLAINE, puis un noeud tous les 2000m
        pkm = PKM_DEBUT_PLAINE + DISTANCE_CASIER * (pkm/1000 - 1)
        y_position = pkm_to_y_position(pkm)
    else:
        y_position = pkm_to_y_position(pkm)

    geom = Point(x_position, y_position)
    noeud.set_geom(geom)

    noeud.comment = f"{noeud} localisé à la position ({geom.x}, {geom.y})"
    sous_modele.ajouter_noeud(noeud)

    logger.debug(f"Ajout {noeud}")
    return noeud


def ajouter_section(section):
    sous_modele.ajouter_section(section)
    section.comment = f"{section}"
    logger.debug(f"Ajout {section}")
    return section



def create_sectionprofil_from_position(trigramme, pk_km):
    nom_section = f"St_{trigramme}{pk_km}"
    if trigramme == TRIGRAMME_AFFLUENT:
        nom_section = re.sub(r'\.([0-9]+)$', r'', nom_section)

    section = SectionProfil(nom_section)

    if trigramme == TRIGRAMME_VIEUX_RHONE:
        date_campagne = '15/03/2025'
    elif trigramme == TRIGRAMME_RETENUE:
        date_campagne = '28/02/2025'
    else:
        date_campagne = '01/01/2025'
    section.comment_profilsection = f"Profil importé de Bathy (campagne du {date_campagne})"

    largeur_sto_d = 60.0
    largeur_maj_d = 40.0
    largeur_min = 500.0
    largeur_maj_g = 40.0
    largeur_sto_g = 60.0

    z_rive = 10.0
    z_sto_maj = 8.0
    z_maj_min = 4.0
    z_thalweg = 0.0

    xt_initial = -10.0  # Borne RD Bathy à xt=0

    xz = np.array([
        (xt_initial, z_rive),
        (largeur_sto_d, z_sto_maj),
        (largeur_maj_d, z_maj_min),
        (largeur_min / 2, z_thalweg),  # Centered thalweg
        (largeur_min / 2, z_maj_min),
        (largeur_maj_g, z_sto_maj),
        (largeur_sto_g, z_rive)
    ])
    xz[:, 0] = xz[:, 0].cumsum()

    xt_limites = np.array([
        xt_initial,
        largeur_sto_d,
        largeur_maj_d,
        largeur_min,
        largeur_maj_g,
        largeur_sto_g,
    ])
    xt_limites = xt_limites.cumsum()

    section.set_xz(xz)
    xt_axe_hydraulique = xt_initial + largeur_sto_d + largeur_maj_d + largeur_min / 2
    section.ajouter_limite_geom(LimiteGeom(LimiteGeom.AXE_HYDRAULIQUE, xt_axe_hydraulique))
    xt_thalweg = xt_initial + largeur_sto_d + largeur_maj_d + largeur_min / 2
    section.ajouter_limite_geom(LimiteGeom(LimiteGeom.THALWEG, xt_thalweg))
    section.set_lits_numerotes(xt_limites)
    # section.ajouter_fente(0.15, 15)
    return section


def ajouter_sectionidem(section_reference):
    idx = 0
    nom_section_candidat = section_reference.id
    while nom_section_candidat in sous_modele.sections:
        assert idx < len(LETTERS_FOR_SECTIONIDEM)
        if idx == 0:
            nom_section_candidat += LETTERS_FOR_SECTIONIDEM[idx]
        else:
            nom_section_candidat = nom_section_candidat[:-1] + LETTERS_FOR_SECTIONIDEM[idx]
        idx += 1
    return ajouter_section(SectionIdem(nom_section_candidat, section_reference, dz_section_reference=0.0))


def ajouter_section_from_position(trigramme, pk_km):
    pkm = pk_km_to_pkm(pk_km)

    try:
        delta_xp = DELTA_XP_BATHY[trigramme]
    except KeyError:
        delta_xp = 1

    if trigramme != TRIGRAMME_RETENUE and pkm in (PKM_RESTITUTION, PKM_DIFFLUENCE):
        nom_section_reference = f"St_{TRIGRAMME_RETENUE}{pk_km}"
        if nom_section_reference in sous_modele.sections:
            section_reference = sous_modele.get_section(nom_section_reference)
        else:
            section_reference = ajouter_section(create_sectionprofil_from_position(TRIGRAMME_RETENUE, pk_km))
        return ajouter_sectionidem(section_reference)  # SectionIdem

    elif pkm % delta_xp == 0:
        nom_section = f"St_{trigramme}{pk_km}"
        if nom_section in sous_modele.sections:
            section_reference = sous_modele.get_section(nom_section)
            if section_reference.xp == -1:
                return section_reference  # SectionProfil
            else:
                return ajouter_sectionidem(section_reference)  # SectionIdem
        else:
            return ajouter_section(create_sectionprofil_from_position(trigramme, pk_km))  # SectionProfil

    else:
        pkm_nearest_bathy = round(pkm / delta_xp) * delta_xp
        pk_km_nearest_bathy = pkm_to_pk_km(pkm_nearest_bathy)

        nom_section_reference = f"St_{trigramme}{pk_km_nearest_bathy}"
        if nom_section_reference in sous_modele.sections:
            section_reference = sous_modele.get_section(nom_section_reference)
        else:
            section_reference = ajouter_section(create_sectionprofil_from_position(trigramme, pk_km_nearest_bathy))
        return ajouter_sectionidem(section_reference)  # SectionIdem


def ajouter_branche(branche, sections_at_xp):
    trigramme_br, pk_km_br = get_trigramme_and_pk_km(branche.id)
    trigramme_nd_am, pk_km_st_am = get_trigramme_and_pk_km(branche.noeud_amont.id)
    if trigramme_br == trigramme_nd_am:
        assert pk_km_br == pk_km_st_am

    for section, xp in sections_at_xp:
        assert section.xp == -1
        branche.ajouter_section_dans_branche(section, xp)
    sous_modele.ajouter_branche(branche)
    branche.comment = f"{branche}"
    logger.debug(f"Ajout {branche}")
    return branche


def ajouter_branche_avec_sections_aux_extremites(branche):
    trigramme_br, pk_km_br = get_trigramme_and_pk_km(branche.id)

    pk_km_am = get_trigramme_and_pk_km(branche.noeud_amont.id)[1]
    pk_km_av = get_trigramme_and_pk_km(branche.noeud_aval.id)[1]
    if trigramme_br == TRIGRAMME_AFFLUENT and pk_km_to_pkm(pk_km_av) == PKM_CONFLUENCE_AFFLUENT:
        # Corrige le PK de l'affluent à la confluence
        pk_km_av = 0

    if branche.type in Branche.TYPES_WITH_GEOM:
        section_am = ajouter_section_from_position(trigramme_br, pk_km_am)
        section_av = ajouter_section_from_position(trigramme_br, pk_km_av)
    else:
        branche_id = branche.id[3:]
        section_am = ajouter_section(SectionSansGeometrie(f'St_{branche_id}_Am'))
        section_av = ajouter_section(SectionSansGeometrie(f'St_{branche_id}_Av'))

    sections_at_xp = [
        (section_am, 0),
    ]
    if trigramme_br == TRIGRAMME_PLAINE:
        xp_aval = DISTANCE_CASIER
    else:
        xp_aval = round(abs(pk_km_to_pkm(pk_km_av) - pk_km_to_pkm(pk_km_am)))  # branche.geom.length can differ!

    # Ajout de SectionProfil intermédiaires
    if isinstance(branche, BrancheSaintVenant) and trigramme_br in DELTA_XP_BATHY:
        delta_xp = DELTA_XP_BATHY[trigramme_br]
        pkm_am = pk_km_to_pkm(pk_km_am)
        pkm_av = pk_km_to_pkm(pk_km_av)
        pkm_min = min(pkm_am, pkm_av)
        pkm_max = max(pkm_am, pkm_av)
        pkm_min_ceil = ceil(pkm_min / delta_xp) * delta_xp
        pkm_max_floor = floor(pkm_max / delta_xp) * delta_xp
        for pkm in np.arange(start=pkm_min_ceil, stop=pkm_max_floor, step=delta_xp):
            if pkm_min < pkm < pkm_max:
                pk_km = pkm_to_pk_km(pkm)
                nom_section = f"St_{trigramme_br}{pk_km}"
                if trigramme_br == TRIGRAMME_AFFLUENT:
                    nom_section = re.sub(r'\.([0-9]+)$', r'', nom_section)
                if nom_section in sous_modele.sections:
                    section = sous_modele.get_section(nom_section)
                else:
                    section = ajouter_section(create_sectionprofil_from_position(trigramme_br, pk_km))
                xp = pkm - pkm_min
                assert 0 < xp < xp_aval
                sections_at_xp.append((section, xp))

    sections_at_xp.append((section_av, xp_aval))

    ajouter_branche(branche, sections_at_xp)

    for section in branche.liste_sections_dans_branche:
        if isinstance(section, SectionProfil):
            section.build_orthogonal_trace(branche.geom)

    return branche


def ajouter_casier(noeud_amont):
    nom_casier = 'Ca_' + noeud_amont.id[3:]
    casier = Casier(nom_casier, noeud_amont)
    casier.comment = f"{casier}"
    profil_casier = ProfilCasier('Pc_' + casier.id[3:] + '_001')
    profil_casier.set_longueur(TAILLE_CASIER)
    profil_casier.set_xz(np.array([(0, 90.0), (TAILLE_CASIER/5, 100.0), (4*TAILLE_CASIER/5, 102.0), (TAILLE_CASIER, 110.0)]))
    profil_casier.comment = f"{profil_casier} calculé avec un MNTerrain"
    casier.ajouter_profil_casier(profil_casier)
    polygon = LinearRing([
        (-TAILLE_CASIER/2, -TAILLE_CASIER/2),
        (-TAILLE_CASIER/2, TAILLE_CASIER/2),
        (TAILLE_CASIER/2, TAILLE_CASIER/2),
        (TAILLE_CASIER/2, -TAILLE_CASIER/2),
    ])
    polygon = translate(polygon, xoff=noeud_amont.geom.x, yoff=noeud_amont.geom.y)
    casier.set_geom(polygon)
    sous_modele.ajouter_casier(casier)


# Ajout des Noeuds
## VRH
nd_vrh_80_000 = ajouter_noeud('Nd_VRH80.000')
nd_vrh_84_900 = ajouter_noeud('Nd_VRH84.900')
nd_vrh_85_100 = ajouter_noeud('Nd_VRH85.100')

## CAF
nd_caf_orphelin = ajouter_noeud('Nd_CAF85.000_orphelin')
nd_caf_87_000 = ajouter_noeud('Nd_CAF87.000')

## RET
nd_ret_90_000 = ajouter_noeud('Nd_RET90.000')
nd_ret_96_000 = ajouter_noeud('Nd_RET96.000_PR1')
nd_ret_98_000 = ajouter_noeud('Nd_RET98.000')
nd_ret_100_500 = ajouter_noeud('Nd_RET100.500')
nd_ret_102_700 = ajouter_noeud('Nd_RET102.700')
nd_ret_103_000 = ajouter_noeud('Nd_RET103.000_PR2')
nd_ret_105_000 = ajouter_noeud('Nd_RET105.000')

## AMB (+ BGE) + AVB
nd_amb = ajouter_noeud('Nd_AMB105.500')
nd_avb_1 = ajouter_noeud('Nd_AVB106.000')
nd_avb_2 = ajouter_noeud('Nd_AVB106.200')

## CAA
nd_caa_1 = ajouter_noeud('Nd_CAA107.500')
nd_caa_2 = ajouter_noeud('Nd_CAA110.000')

## CAS
nd_cas_1 = ajouter_noeud('Nd_CAS1')
nd_cas_2 = ajouter_noeud('Nd_CAS2')
nd_cas_3 = ajouter_noeud('Nd_CAS3')
nd_cas_4 = ajouter_noeud('Nd_CAS4')
nd_cas_5 = ajouter_noeud('Nd_CAS5')

## AFF
nd_aff_amont = ajouter_noeud('Nd_AFF5')
nd_aff_milieu = ajouter_noeud('Nd_AFF3')


# Ajout des Branches
## VRH
br_vrh_1 = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_VRH80.000', nd_vrh_80_000, nd_vrh_84_900)
)
br_vrh_2 = ajouter_branche_avec_sections_aux_extremites(
    BrancheSeuilTransversal('Br_VRH84.900_Seuil', nd_vrh_84_900, nd_vrh_85_100)
)
br_vrh_3 = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_VRH85.100', nd_vrh_85_100, nd_ret_90_000)
)

## CAF
br_caf = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_CAF87.000', nd_caf_87_000, nd_ret_90_000)
)

## RET
br_ret_1 = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET90.000', nd_ret_90_000, nd_ret_96_000)
)
br_ret_1bis = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET96.000', nd_ret_96_000, nd_ret_98_000)
)
br_ret_2 = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET98.000', nd_ret_98_000, nd_ret_100_500)
)
br_ret_3 = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET100.500', nd_ret_100_500, nd_ret_102_700)
)
br_ret_4 = ajouter_branche_avec_sections_aux_extremites(
    BranchePdC('Br_RET102.700_Pont', nd_ret_102_700, nd_ret_103_000)
)
br_ret_6 = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET103.000', nd_ret_103_000, nd_ret_105_000)
)

## AMB + BGE + AVB
br_amb = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_AMB105.000', nd_ret_105_000, nd_amb)
)
br_bge = ajouter_branche_avec_sections_aux_extremites(
    BrancheBarrageFilEau('Br_BGE105.500', nd_amb, nd_avb_1)
)
br_avb = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_AVB106.000', nd_avb_1, nd_avb_2)
)

## CAA
br_caa_1 = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_CAA105.000', nd_ret_105_000, nd_caa_1)
)
br_caa_2 = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_CAA107.500', nd_caa_1, nd_caa_2)
)

## AFF
br_aff_amont = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_AFF5', nd_aff_amont, nd_aff_milieu)
)
br_aff_aval = ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_AFF3', nd_aff_milieu, nd_ret_100_500)
)

## RET vers CAS (mais la branche appartient à la zone CAS)
br_ret_cas1 = ajouter_branche_avec_sections_aux_extremites(
    BrancheSeuilLateral('Br_CAS1_RET', nd_ret_96_000, nd_cas_1)
)
br_cas5_ret = ajouter_branche_avec_sections_aux_extremites(
    BrancheOrifice('Br_CAS5_RET', nd_cas_5, nd_ret_105_000)
)
br_cas2_ret = ajouter_branche_avec_sections_aux_extremites(
    BrancheOrifice('Br_CAS2_RET', nd_ret_98_000, nd_cas_2)
)
br_cas3_ret = ajouter_branche_avec_sections_aux_extremites(
    BrancheOrifice('Br_CAS3_RET', nd_ret_100_500, nd_cas_3)
)
br_cas4_ret = ajouter_branche_avec_sections_aux_extremites(
    BrancheSeuilLateral('Br_CAS4_RET', nd_ret_102_700, nd_cas_4)
)
br_cas4_ret.formule_pertes_de_charge = 'Divergent'  # 'Borda' par défaut
br_cas4_ret.set_liste_elements_seuil(np.array([
    (50.0, 100.0, 0.9, 0.9),
    (40.0, 102.0, 0.9, 0.9),
    (60.0, 103.0, 0.9, 0.9),
]))

## CAS
br_cas1_2 = ajouter_branche_avec_sections_aux_extremites(
    BrancheStrickler('Br_CAS1-2', nd_cas_1, nd_cas_2)
)
br_cas2_3 = ajouter_branche_avec_sections_aux_extremites(
    BrancheNiveauxAssocies('Br_CAS2-3', nd_cas_2, nd_cas_3)
)
br_cas3_4 = ajouter_branche_avec_sections_aux_extremites(
    BrancheOrifice('Br_CAS3-4', nd_cas_3, nd_cas_4)
)
br_cas4_5 = ajouter_branche_avec_sections_aux_extremites(
    BrancheStrickler('Br_CAS4-5', nd_cas_4, nd_cas_5)
)


# Peupler une branche pour avoir des SectionInterpolee
sous_modele.peupler_branche_fluviale_avec_sectioninterpolees(br_caa_2.id, 100.0)

br_aff_amont.is_active = False  # Désactiver une branche

br_bge.section_pilote = br_ret_2.get_section_amont()  # Remplace le None par défaut


# Ajout des casiers
ajouter_casier(nd_cas_1)
ajouter_casier(nd_cas_2)
ajouter_casier(nd_cas_3)
ajouter_casier(nd_cas_4)
ajouter_casier(nd_cas_5)


sous_modele.metadata['Commentaire'] = sous_modele.summary() + '\n\n' + get_file_docstring(__file__)


if __name__ == "__main__":
    # logger.setLevel(logging.DEBUG)

    folder = os.path.join('out', 'Sm_single_sm')

    # Write all SousModele files
    sous_modele.write_all(folder, 'Config')

    # Perform some checks
    logger.info('Etapes de validation')
    sous_modele.log_validation()  # could be called before `write_all`
    sous_modele.log_check_xml(folder)  # has to be called after `write_all`
