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
from crue10.emh.section import DEFAULT_FK_STO_ID, DEFAULT_FK_MIN_ID, DEFAULT_FK_MAJ_ID, \
    LimiteGeom, SectionIdem, SectionProfil, SectionSansGeometrie
from crue10.sous_modele import SousModele
from crue10.tests import DEFAULT_METADATA
from crue10.utils import logger


TRIGRAMME_AFFLUENT = 'AFF'
TRIGRAMME_PLAINE_A = 'CCA'
TRIGRAMME_PLAINE_B = 'CCB'
TRIGRAMME_RETENUE = 'RET'
TRIGRAMME_VIEUX_RHONE = 'VRH'

DISTANCE_CASIER = 2000
TAILLE_CASIER = 1800


PKM_VRH_SEUIL = (84900, 85100)
PKM_RESTITUTION = 90000
PKM_DEBUT_PLAINE_A = 86000
PKM_DEBUT_PLAINE_B = PKM_DEBUT_PLAINE_A + 2 * DISTANCE_CASIER + 500
PKM_CONFLUENCE_AFFLUENT = 100500
PKM_RET_PONT = (102700, 103000)
PKM_PR2 = 104000
PKM_DIFFLUENCE = 105000
PKM_BGE = (105600, 106000)

DELTA_XP_BATHY = {  # Distances entre 2 profils Bathy en mètres
    TRIGRAMME_AFFLUENT: 1000,
    TRIGRAMME_RETENUE: 200,
    TRIGRAMME_VIEUX_RHONE: 400,
    'CAA': 250,
    'CAF': 500,
}

X_CENTERED_VALUE = 800000  # Pour que ça ressemble à une abscisse en Lambert 93 sur le Rhône
Y_OFFSET = 6400000  # Pour que ça ressemble à une ordonnées en Lambert 93 sur le Rhône

LETTERS_FOR_SECTIONIDEM = ['a', 'b', 'c']


class SousModeleFromScratch:

    def __init__(self, nom_sous_modele):
        self.sous_modele = SousModele(nom_sous_modele, metadata=DEFAULT_METADATA, mode='w')
        self.sous_modele.ajouter_lois_frottement_par_defaut()

    def ajouter_noeud(self, noeud):
        logger.debug(f"Ajout {noeud}")
        self.sous_modele.ajouter_noeud(noeud)
        return noeud

    def ajouter_section(self, section):
        self.sous_modele.ajouter_section(section)
        section.comment = f"{section}"
        logger.debug(f"Ajout {section}")
        return section

    def creer_sectionprofil_depuis_position(self, trigramme, pk_km):
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

        if trigramme == TRIGRAMME_VIEUX_RHONE:
            xt_initial = -100.0  # Borne RD Bathy à xt=0

            largeur_sto_d = 150.0
            largeur_maj_d = 40.0
            largeur_min = 800.0
            largeur_maj_g = 40.0
            largeur_sto_g = 20.0

            xt_axe_hydraulique = xt_initial + largeur_sto_d + largeur_maj_d + largeur_min / 4  # plus à droite

        elif trigramme == TRIGRAMME_RETENUE:
            xt_initial = -100.0  # Borne RD Bathy à xt=0

            largeur_sto_d = 60.0
            largeur_maj_d = 40.0
            largeur_min = 650.0
            largeur_maj_g = 40.0
            largeur_sto_g = 60.0

            xt_axe_hydraulique = xt_initial + largeur_sto_d + largeur_maj_d + largeur_min / 2  # milieu

        else:
            xt_initial = 0.0  # Borne RD Bathy à xt=0

            largeur_sto_d = 60.0
            largeur_maj_d = 40.0
            largeur_min = 500.0
            largeur_maj_g = 40.0
            largeur_sto_g = 60.0

            xt_axe_hydraulique = xt_initial + largeur_sto_d + largeur_maj_d + largeur_min / 2  # milieu

        z_rive = 10.0
        z_sto_maj = 8.0
        z_maj_min = 4.0
        z_min = 0.1
        z_thalweg = 0.0

        xz = np.array([
            (xt_initial, z_rive),
            (largeur_sto_d, z_sto_maj),
            (largeur_maj_d, z_maj_min),
            (largeur_min / 4, z_min),
            (largeur_min / 4, z_thalweg),  # thalweg au centre du lit mineur
            (largeur_min / 4, z_min),
            (largeur_min / 4, z_maj_min),
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

        xt_thalweg = xt_initial + largeur_sto_d + largeur_maj_d + largeur_min / 2  # thalweg au centre du lit mineur
        section.ajouter_limite_geom(LimiteGeom(LimiteGeom.THALWEG, xt_thalweg))
        section.ajouter_limite_geom(LimiteGeom(LimiteGeom.AXE_HYDRAULIQUE, xt_axe_hydraulique))

        loi_sto = self.sous_modele.get_loi_frottement(DEFAULT_FK_STO_ID)
        loi_maj = self.sous_modele.get_loi_frottement(DEFAULT_FK_MAJ_ID)
        loi_min = self.sous_modele.get_loi_frottement(DEFAULT_FK_MIN_ID)
        section.set_lits_numerotes(xt_limites, [
            loi_sto,
            loi_maj,
            loi_min,
            loi_maj,
            loi_sto,
        ])

        # section.ajouter_fente(0.15, 15)
        return section

    def determiner_nom_section_disponible(self, nom_section_candidat):
        idx = 0
        nom_section_final = nom_section_candidat
        while nom_section_final in self.sous_modele.sections:
            assert idx < len(LETTERS_FOR_SECTIONIDEM)
            if idx == 0:
                nom_section_final += LETTERS_FOR_SECTIONIDEM[idx]
            else:
                nom_section_final = nom_section_final[:-1] + LETTERS_FOR_SECTIONIDEM[idx]
            idx += 1
        return nom_section_final

    def ajouter_sectionidem(self, section_reference, diff_pkm):
        pkm_reference = pk_km_to_pkm(get_trigramme_and_pk_km(section_reference.id)[1])
        nom_section_candidat = self.determiner_nom_section_disponible(section_reference.id)
        pkm_idem = pk_km_to_pkm(get_trigramme_and_pk_km(nom_section_candidat)[1])
        dz_section_reference = diff_pkm / 1000   # pente à 1/1000
        section_idem = SectionIdem(nom_section_candidat, section_reference, dz_section_reference=dz_section_reference)
        return self.ajouter_section(section_idem)

    def ajouter_section_from_position(self, trigramme, pk_km):
        pkm = pk_km_to_pkm(pk_km)

        try:
            delta_xp = DELTA_XP_BATHY[trigramme]
        except KeyError:
            delta_xp = 1

        if trigramme == 'BGE':  # On corriger le nom autour du barrage
            if pkm == PKM_BGE[0]:
                trigramme = 'AMB'
            elif pkm == PKM_BGE[1]:
                trigramme = 'AVB'
            else:
                raise NotImplementedError

        if trigramme not in (TRIGRAMME_RETENUE, 'CAA') and pkm in (PKM_RESTITUTION, PKM_DIFFLUENCE):
            nom_section_reference = f"St_{TRIGRAMME_RETENUE}{pk_km}"
            if nom_section_reference in self.sous_modele.sections:
                section_reference = self.sous_modele.get_section(nom_section_reference)
            else:
                section_reference = self.ajouter_section(self.creer_sectionprofil_depuis_position(TRIGRAMME_RETENUE, pk_km))
            return self.ajouter_sectionidem(section_reference, 0)  # SectionIdem

        elif trigramme == TRIGRAMME_RETENUE and pkm == PKM_PR2:
            section = self.creer_sectionprofil_depuis_position(trigramme, pk_km)
            if self.sous_modele.id.endswith('amont_min'):
                section.id = section.id + 'bis'
                section.set_profilsection_name()
            return self.ajouter_section(section)

        elif pkm % delta_xp == 0:
            nom_section = f"St_{trigramme}{pk_km}"
            if nom_section in self.sous_modele.sections:
                section_reference = self.sous_modele.get_section(nom_section)
                if section_reference.xp == -1:
                    return section_reference  # SectionProfil
                else:
                    return self.ajouter_sectionidem(section_reference, 0)  # SectionIdem
            else:
                return self.ajouter_section(self.creer_sectionprofil_depuis_position(trigramme, pk_km))  # SectionProfil

        else:
            assert trigramme not in (TRIGRAMME_PLAINE_A, TRIGRAMME_PLAINE_B)

            pkm_nearest_bathy = round(pkm / delta_xp) * delta_xp
            pk_km_nearest_bathy = pkm_to_pk_km(pkm_nearest_bathy)

            nom_section_reference = f"St_{trigramme}{pk_km_nearest_bathy}"
            if nom_section_reference in self.sous_modele.sections:
                section_reference = self.sous_modele.get_section(nom_section_reference)
            else:
                section_reference = self.ajouter_section(self.creer_sectionprofil_depuis_position(trigramme, pk_km_nearest_bathy))
            diff_pkm = pkm_nearest_bathy - pkm
            return self.ajouter_sectionidem(section_reference, diff_pkm)  # SectionIdem

    def ajouter_branche(self, branche, sections_at_xp):
        trigramme_br, pk_km_br = get_trigramme_and_pk_km(branche.id)
        trigramme_nd_am, pk_km_st_am = get_trigramme_and_pk_km(branche.noeud_amont.id)
        if trigramme_br == trigramme_nd_am:
            assert pk_km_br == pk_km_st_am

        for section, xp in sections_at_xp:
            assert section.xp == -1
            branche.ajouter_section_dans_branche(section, xp)

        if branche.noeud_amont.id not in self.sous_modele.noeuds:
            self.sous_modele.ajouter_noeud(branche.noeud_amont)
        if branche.noeud_aval.id not in self.sous_modele.noeuds:
            self.sous_modele.ajouter_noeud(branche.noeud_aval)
        self.sous_modele.ajouter_branche(branche)

        branche.comment = f"{branche}"
        logger.debug(f"Ajout {branche}")
        return branche

    def ajouter_branche_avec_sections_aux_extremites(self, branche):
        trigramme_br, pk_km_br = get_trigramme_and_pk_km(branche.id)

        pk_km_am = get_trigramme_and_pk_km(branche.noeud_amont.id)[1]
        pk_km_av = get_trigramme_and_pk_km(branche.noeud_aval.id)[1]
        if trigramme_br == TRIGRAMME_AFFLUENT and pk_km_to_pkm(pk_km_av) == PKM_CONFLUENCE_AFFLUENT:
            # Corrige le PK de l'affluent à la confluence
            pk_km_av = 0

        if branche.type in Branche.TYPES_WITH_GEOM:
            section_am = self.ajouter_section_from_position(trigramme_br, pk_km_am)
            section_av = self.ajouter_section_from_position(trigramme_br, pk_km_av)
        else:
            branche_id = branche.id[3:]
            section_am = self.ajouter_section(SectionSansGeometrie(f'St_{branche_id}_Am'))
            section_av = self.ajouter_section(SectionSansGeometrie(f'St_{branche_id}_Av'))

        sections_at_xp = [
            (section_am, 0),
        ]
        if trigramme_br in (TRIGRAMME_PLAINE_A, TRIGRAMME_PLAINE_B):
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
                    if nom_section in self.sous_modele.sections:
                        section = self.sous_modele.get_section(nom_section)
                    else:
                        section = self.ajouter_section(self.creer_sectionprofil_depuis_position(trigramme_br, pk_km))
                    xp = pkm - pkm_min
                    assert 0 < xp < xp_aval
                    sections_at_xp.append((section, xp))

        sections_at_xp.append((section_av, xp_aval))

        self.ajouter_branche(branche, sections_at_xp)

        if branche.type in Branche.TYPES_WITH_GEOM:
            branche.construire_traces_geometriques_des_sectionprofils()

        return branche

    def ajouter_casier(self, noeud_amont):
        nom_casier = 'Ca_' + noeud_amont.id[3:]
        casier = Casier(nom_casier, noeud_amont)
        casier.comment = f"{casier}"
        profil_casier = ProfilCasier('Pc_' + casier.id[3:] + '_001')
        profil_casier.set_longueur(TAILLE_CASIER)
        profil_casier.set_xz(np.array([
            (0, 118.24),
            (1.714, 118.54),
            (1.926, 118.84),
            (2.091, 119.14),
            (2.391, 119.44),
            (5.1878, 119.694613),
            (6.314, 119.74),
            (8.3368, 119.756987),
            (60.745, 120.04),
            (184.213, 120.34),
            (236.537, 120.64),
            (263.117, 120.94),
            (290.491, 121.24),
            (321.114, 121.54),
            (337.802, 121.84),
            (354.29, 122.14),
            (366.314, 122.44),
            (375.528, 122.74),
            (381.639, 123.04),
            (390.046, 123.34),
            (397.175, 123.64),
            (402.742, 123.94),
            (407.087, 124.24),
            (410.578, 124.54),
            (414.414, 124.84),
            (418.234, 125.14),
            (422.327, 125.44),
            (425.579, 125.74),
            (428.33, 126.04),
            (430.495, 126.34),
            (432.362, 126.64),
            (434.375, 126.94),
            (437.042, 127.24),
            (439.264, 127.54),
            (441.482, 127.84),
            (442.609, 128.14),
            (443.334, 128.44),
            (444.173, 128.74),
            (444.959, 129.04),
            (445.754, 129.34),
            (446.096, 129.64),
        ]))
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
        self.sous_modele.ajouter_casier(casier)

    def preparer(self):
        suffixe = self.sous_modele.id[2:].replace('bge', '').replace('amont_min', 'amont')
        self.sous_modele.rename_emhs(suffixe, emh_list=['Fk'])
        self.sous_modele.set_comment(self.sous_modele.summary())


# Define helpers
def pk_km_to_pkm(pk_km):
    return 1000 * float(pk_km)


def pkm_to_pk_km(pkm):
    return "{:,.0f}".format(pkm).replace(',', '.')


def pkm_to_y_position(pk):
    return Y_OFFSET - pk


def get_trigramme_and_pk_km(nom_emh):
    """Retourne le trigramme et le PK à partir du nom de l'EMH"""
    if '-' in nom_emh:
        match = re.match(r'^(Br|Nd|St)_(?P<trigramme_am>[A-Z]{3})(?P<complement_am>[\w]*?)(?P<pk_km>[0-9.]+)?-(?P<trigramme>[A-Z]{3})(?P<pk_km_av>[0-9.]+)(?P<complement_av>[\w]*?)$', nom_emh)
    else:
        match = re.match(r'^(Br|Nd|St)_(?P<trigramme>[A-Z]{3})(?P<pk_km>[0-9.]+)?(?P<complement>[\w]*?)$', nom_emh)

    pk_km = match.group('pk_km')
    if pk_km is None:
        # Hardcoded determination of PK for specific locations
        if 'Seuil_Av' in nom_emh:
            pkm = PKM_VRH_SEUIL[1]
        elif 'Seuil' in nom_emh:
            pkm = PKM_VRH_SEUIL[0]
        elif 'Pont_Av' in nom_emh:
            pkm = PKM_RET_PONT[1]
        elif 'Pont' in nom_emh:
            pkm = PKM_RET_PONT[0]
        elif 'BGE_XX_Av' in nom_emh:
            pkm = PKM_BGE[1]
        elif 'BGE_XX' in nom_emh:
            pkm = PKM_BGE[0]
        else:
            raise NotImplementedError
        pk_km = pkm_to_pk_km(pkm)

    return match.group('trigramme'), pk_km


def creer_noeud(nom_noeud):
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
    elif trigramme == TRIGRAMME_PLAINE_A:
        x_position -= 2500
    elif trigramme == TRIGRAMME_PLAINE_B:
        x_position -= 1500

    if trigramme == TRIGRAMME_AFFLUENT:
        y_position = pkm_to_y_position(PKM_CONFLUENCE_AFFLUENT)
    elif trigramme == TRIGRAMME_PLAINE_A:  # CCA01 sera à PKM_DEBUT_PLAINE_A, puis un noeud tous les 2000m
        pkm = PKM_DEBUT_PLAINE_A + DISTANCE_CASIER * (pkm / 1000 - 1)
        y_position = pkm_to_y_position(pkm)
    elif trigramme == TRIGRAMME_PLAINE_B:  # CCB01 sera à PKM_DEBUT_PLAINE_B, puis un noeud tous les 2000m
        pkm = PKM_DEBUT_PLAINE_B + DISTANCE_CASIER * (pkm / 1000 - 1)
        y_position = pkm_to_y_position(pkm)
    else:
        y_position = pkm_to_y_position(pkm)

    geom = Point(x_position, y_position)
    noeud.set_geom(geom)

    noeud.comment = f"{noeud} localisé à la position ({geom.x}, {geom.y})"
    return noeud


smfs_amont_min = SousModeleFromScratch('Sm_amont_min')  # VRH + CAF + RET (jusqu'au PR2) + AFF
smfs_plaine = SousModeleFromScratch('Sm_plaine')  # CCA + CCB
smfs_canal_amenee = SousModeleFromScratch('Sm_canal_amenee')  # CAA
smfs_bgefileau = SousModeleFromScratch('Sm_bgefileau')  # RET (depuis PR2) + AMB + BGE + AVB
smfs_bgegen = SousModeleFromScratch('Sm_bgegen')  # RET (depuis PR2) + AMB + BGE + AVB


mo_mono_sm = []
mo_multi_sm_avec_bgefileau = []
mo_multi_sm_avec_bgegen = []


# Ajout des Noeuds
## VRH
nd_vrh_1 = creer_noeud('Nd_VRH80.000')
nd_vrh_2 = creer_noeud('Nd_VRH_Seuil_Am')
nd_vrh_3 = creer_noeud('Nd_VRH_Seuil_Av')
nd_vrh_4 = creer_noeud('Nd_VRH87.600')

## CAF
nd_caf_orphelin = creer_noeud('Nd_CAF85.000_orphelin')
nd_caf_87_000 = creer_noeud('Nd_CAF87.000')

## RET
nd_ret_90_000 = creer_noeud('Nd_RET90.000')
nd_ret_92_000 = creer_noeud('Nd_RET92.000')
nd_ret_96_000 = creer_noeud('Nd_RET96.000')
nd_ret_98_000 = creer_noeud('Nd_RET98.000_PR1')
nd_ret_100_500 = creer_noeud('Nd_RET100.500')
nd_ret_102_700 = creer_noeud('Nd_RET_Pont_Am')
nd_ret_102_900 = creer_noeud('Nd_RET102.900')
nd_ret_104_000_pr2 = creer_noeud('Nd_RET104.000_PR2')
nd_ret_105_000 = creer_noeud('Nd_RET105.000')

## AMB (+ BGE) + AVB
nd_amb = creer_noeud('Nd_AMB105.600')
nd_avb_1 = creer_noeud('Nd_AVB106.000')
nd_avb_2 = creer_noeud('Nd_AVB106.020')

## CAA
nd_caa_1 = creer_noeud('Nd_CAA107.500')
nd_caa_2 = creer_noeud('Nd_CAA110.000')

## CCA
nd_cca_1 = creer_noeud('Nd_CCA01')
nd_cca_2 = creer_noeud('Nd_CCA02')
nd_ccb_1 = creer_noeud('Nd_CCB01')
nd_ccb_2 = creer_noeud('Nd_CCB02')
nd_ccb_3 = creer_noeud('Nd_CCB03')

## AFF
nd_aff_amont = creer_noeud('Nd_AFF5')
nd_aff_milieu = creer_noeud('Nd_AFF3')


# Ajout des Branches
## VRH
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_VRH80.000', nd_vrh_1, nd_vrh_2)
)
br_vrh_seuil = smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSeuilTransversal('Br_VRH_Seuil', nd_vrh_2, nd_vrh_3)
)
br_vrh_seuil.set_liste_elements_seuil_avec_coef_par_defaut(np.array([
    (1000.0, 100.0),
]))
br_vrh_seuil.decouper_seuil_elem(50, 5.0)
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_VRH85.100', nd_vrh_3, nd_vrh_4)
)
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_VRH87.600', nd_vrh_4, nd_ret_90_000)
)

## CAF
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_CAF87.000', nd_caf_87_000, nd_ret_90_000)
)

## RET
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET90.000', nd_ret_90_000, nd_ret_92_000)
)
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET92.000', nd_ret_92_000, nd_ret_96_000)
)
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET96.000', nd_ret_96_000, nd_ret_98_000)
)
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET98.000', nd_ret_98_000, nd_ret_100_500)
)
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET100.500', nd_ret_100_500, nd_ret_102_700)
)
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BranchePdC('Br_RET_Pont', nd_ret_102_700, nd_ret_102_900)
)
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET102.900', nd_ret_102_900, nd_ret_104_000_pr2)
)

br_bgefileau_aval_pr2 = smfs_bgefileau.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET104.000', nd_ret_104_000_pr2, nd_ret_105_000)
)
br_bgegen_aval_pr2 = smfs_bgegen.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_RET104.000', nd_ret_104_000_pr2, nd_ret_105_000)
)

## AMB + BGE (avec BrancheBarrageFilEau) + AVB
br_amb_fileau = smfs_bgefileau.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_AMB105.000', nd_ret_105_000, nd_amb)
)
br_bgefileau = smfs_bgefileau.ajouter_branche_avec_sections_aux_extremites(
    BrancheBarrageFilEau('Br_BGE_XX', nd_amb, nd_avb_1)
)
smfs_bgefileau.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_AVB106.000', nd_avb_1, nd_avb_2)
)

## AMB + BGE (avec BrancheBarrageGenerique) + AVB
br_amb_generique = smfs_bgegen.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_AMB105.000', nd_ret_105_000, nd_amb)
)
br_bgegen = smfs_bgegen.ajouter_branche_avec_sections_aux_extremites(
    BrancheBarrageGenerique('Br_BGE_XX', nd_amb, nd_avb_1)
)
smfs_bgegen.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_AVB106.000', nd_avb_1, nd_avb_2)
)

## CAA
smfs_canal_amenee.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_CAA105.000', nd_ret_105_000, nd_caa_1)
)
br_caa_2 = smfs_canal_amenee.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_CAA107.500', nd_caa_1, nd_caa_2)
)

## AFF
br_aff_amont = smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_AFF5', nd_aff_amont, nd_aff_milieu)
)
smfs_amont_min.ajouter_branche_avec_sections_aux_extremites(
    BrancheSaintVenant('Br_AFF3', nd_aff_milieu, nd_ret_100_500)
)

## RET vers CCA et CCB (mais la branche appartient toujours à la zone CCA ou CCB)
smfs_plaine.ajouter_branche_avec_sections_aux_extremites(
    BrancheSeuilLateral('Br_VRH_Seuil-CCA01', nd_vrh_3, nd_cca_1)
)
smfs_plaine.ajouter_branche_avec_sections_aux_extremites(
    BrancheOrifice('Br_VRH87.600-CCA02', nd_vrh_4, nd_cca_2)
)
smfs_plaine.ajouter_branche_avec_sections_aux_extremites(
    BrancheOrifice('Br_RET90.000-CCB01', nd_ret_90_000, nd_ccb_1)
)
br_cas4_ret = smfs_plaine.ajouter_branche_avec_sections_aux_extremites(
    BrancheSeuilLateral('Br_RET92.000-CCB02', nd_ret_92_000, nd_ccb_2)
)
br_cas4_ret.formule_pertes_de_charge = 'Divergent'  # 'Borda' par défaut
br_cas4_ret.set_liste_elements_seuil(np.array([
    (50.0, 100.0, 0.9, 0.9),
    (40.0, 102.0, 0.9, 0.9),
    (60.0, 103.0, 0.9, 0.9),
]))
smfs_plaine.ajouter_branche_avec_sections_aux_extremites(
    BrancheOrifice('Br_RET96.000-CCB03', nd_ret_96_000, nd_ccb_3)
)

## CAS
smfs_plaine.ajouter_branche_avec_sections_aux_extremites(
    BrancheStrickler('Br_CCA01_02', nd_cca_1, nd_cca_2)
)
smfs_plaine.ajouter_branche_avec_sections_aux_extremites(
    BrancheNiveauxAssocies('Br_CCA02-CCB01', nd_cca_2, nd_ccb_1)
)
smfs_plaine.ajouter_branche_avec_sections_aux_extremites(
    BrancheStrickler('Br_CCB01_02', nd_ccb_1, nd_ccb_2)
)
smfs_plaine.ajouter_branche_avec_sections_aux_extremites(
    BrancheStrickler('Br_CCB02_03', nd_ccb_2, nd_ccb_3)
)


smfs_amont_min.ajouter_noeud(nd_caf_orphelin)  # Ajout noeud orphelin

# Peupler une branche pour avoir des SectionInterpolee
smfs_canal_amenee.sous_modele.peupler_branche_fluviale_avec_sectioninterpolees(br_caa_2.id, 100.0)

br_aff_amont.is_active = False  # Désactiver une branche

br_bgefileau.section_pilote = br_bgefileau_aval_pr2.get_section_amont()  # Remplace le None par défaut
br_bgegen.section_pilote = br_bgegen_aval_pr2.get_section_amont()  # Remplace le None par défaut


# Ajout des casiers
smfs_plaine.ajouter_casier(nd_cca_1)
smfs_plaine.ajouter_casier(nd_cca_2)
smfs_plaine.ajouter_casier(nd_ccb_1)
smfs_plaine.ajouter_casier(nd_ccb_2)
smfs_plaine.ajouter_casier(nd_ccb_3)


for smfs in [smfs_amont_min, smfs_plaine, smfs_canal_amenee, smfs_bgefileau, smfs_bgegen]:
    smfs.preparer()


if __name__ == "__main__":
    # logger.setLevel(logging.DEBUG)

    for sm in [smfs_amont_min, smfs_plaine, smfs_canal_amenee, smfs_bgefileau, smfs_bgegen]:
        folder = os.path.join('..', 'tmp', 'Sm_from_scratch', sm.sous_modele.id)

        # Write all SousModele files
        sm.sous_modele.write_all(folder, 'Config')

        # Perform some checks
        logger.info('Etapes de validation')
        sm.sous_modele.log_validation()  # could be called before `write_all`
        sm.sous_modele.log_check_xml(folder)  # has to be called after `write_all`
