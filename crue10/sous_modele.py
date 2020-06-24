# coding: utf-8
from builtins import super  # Python2 fix (requires module `future`)
from collections import OrderedDict
import fiona
import numpy as np
import os.path
from shapely.geometry import LinearRing, LineString, mapping, Point

from crue10.base import FichierXML
from crue10.emh.branche import BRANCHE_CLASSES, Branche, BranchePdC, BrancheSeuilTransversal, \
    BrancheSeuilLateral, BrancheOrifice, BrancheStrickler, BrancheNiveauxAssocies, \
    BrancheBarrageGenerique, BrancheBarrageFilEau, BrancheSaintVenant
from crue10.emh.casier import Casier, ProfilCasier
from crue10.emh.noeud import Noeud
from crue10.emh.section import DEFAULT_FK_MAX, DEFAULT_FK_MIN, DEFAULT_FK_STO, LoiFrottement, \
    LimiteGeom, LitNumerote, Section, SectionIdem, SectionInterpolee, SectionProfil, SectionSansGeometrie
from crue10.utils import check_isinstance, check_preffix, ExceptionCrue10, ExceptionCrue10GeometryNotFound, \
    get_optional_commentaire, logger, parse_loi, PREFIX


def parse_elem_seuil(elt, with_pdc=False):
    length = 4 if with_pdc else 3
    elt_group = elt.findall(PREFIX + ('ElemSeuilAvecPdc' if with_pdc else 'ElemSeuil'))
    values = []
    for elem in elt_group:
        row = [
            float(elem.find(PREFIX + 'Largeur').text),
            float(elem.find(PREFIX + 'Zseuil').text),
            float(elem.find(PREFIX + 'CoefD').text),
        ]
        if with_pdc:
            row.append(float(elem.find(PREFIX + 'CoefPdc').text))
        if len(row) != length:
            raise RuntimeError
        values.append(row)
    return np.array(values)


class SousModele(FichierXML):
    """
    Sous-modèle Crue10

    :param id: nom du sous-modèle
    :type id: str
    :param noeuds: dictionnaire ordonné des noeuds
    :type noeuds: OrderedDict(Noeud)
    :param sections: dictionnaire ordonné des sections
        (SectionProfil, SectionIdem, SectionInterpolee or SectionSansGeometrie)
    :type sections: OrderedDict(Section
    :param branches: dictionnaire ordonné des branches
    :type branches: OrderedDict(Branche)
    :param casiers: dictionnaire ordonné des casiers
    :type casiers: OrderedDict(Casier
    :param profils_casier: dictionnaire ordonné des profils casier
    :type profils_casier: OrderedDict(ProfilCasier)
    :param lois_frottement: dictionnaire ordonné des lois de frottement (coefficients de Strickler)
    :type lois_frottement: OrderedDict(LoiFrottement)
    """

    FILES_SHP = ['noeuds', 'branches', 'casiers', 'tracesSections']
    FILES_XML = ['drso', 'dcsp', 'dptg', 'dfrt']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, nom_sous_modele, access='r', files=None, metadata=None):
        """
        :param nom_sous_modele: nom du sous-modèle
        :type nom_sous_modele: str
        :param access: accès en lecture ('r') ou écriture ('w')
        :type access: str
        :param files: dictionnaire des chemins vers les fichiers xml
        :type files: dict(str)
        :param metadata: dictionnaire avec les méta-données
        :type metadata: dict(str)
        """
        check_preffix(nom_sous_modele, 'Sm_')
        self.id = nom_sous_modele
        super().__init__(access, files, metadata)

        self.noeuds = OrderedDict()
        self.sections = OrderedDict()
        self.branches = OrderedDict()
        self.casiers = OrderedDict()
        self.profils_casier = OrderedDict()
        self.lois_frottement = OrderedDict()

    def ajouter_noeud(self, noeud):
        check_isinstance(noeud, Noeud)
        if noeud.id in self.noeuds:
            raise ExceptionCrue10("Le noeud %s est déjà présent" % noeud.id)
        self.noeuds[noeud.id] = noeud

    def ajouter_section(self, section):
        check_isinstance(section, [SectionProfil, SectionIdem, SectionSansGeometrie, SectionInterpolee])
        if section.id in self.sections:
            raise ExceptionCrue10("La Section `%s` est déjà présente" % section.id)
        if isinstance(section, SectionIdem):
            if section.section_reference.id not in self.sections:
                raise ExceptionCrue10("La SectionIdem `%s` fait référence à une SectionProfil inexistante `%s`"
                                      % (section.id, section.section_ori.id))
        if isinstance(section, SectionProfil):
            for lit in section.lits_numerotes:
                if lit.loi_frottement.id not in self.lois_frottement:
                    raise ExceptionCrue10("La loi de frottement %s de la section `%s` doit être"
                                          " ajoutée au sous-modèle avant" % (lit.loi_frottement.id, section.id))
        self.sections[section.id] = section

    def ajouter_branche(self, branche):
        check_isinstance(branche, BRANCHE_CLASSES)
        if branche.id in self.branches:
            raise ExceptionCrue10("La branche `%s` est déjà présente" % branche.id)
        if branche.noeud_amont.id not in self.noeuds:
            raise ExceptionCrue10("Le noeud amont %s de la branche `%s` doit être ajouté au sous-modèle avant"
                                  % (branche.noeud_amont.id, branche.id))
        if branche.noeud_aval.id not in self.noeuds:
            raise ExceptionCrue10("Le noeud aval %s de la branche `%s` doit être ajouté au sous-modèle avant"
                                  % (branche.noeud_aval.id, branche.id))
        self.branches[branche.id] = branche

    def ajouter_casier(self, casier):
        check_isinstance(casier, Casier)
        if casier.id in self.casiers:
            raise ExceptionCrue10("Le casier %s est déjà présent" % casier.id)
        if casier.noeud_reference.id not in self.noeuds:
            raise ExceptionCrue10("Le noeud_reference %s du casier `%s` doit être ajouté au sous-modèle avant"
                                  % (casier.noeud_reference.id, casier.id))
        for profilcasier in casier.profils_casier:
            if profilcasier.id not in self.profils_casier:
                self.ajouter_profil_casier(profilcasier)
        self.casiers[casier.id] = casier

    def ajouter_profil_casier(self, profil_casier):
        check_isinstance(profil_casier, ProfilCasier)
        if profil_casier.id in self.profils_casier:
            raise ExceptionCrue10("Le profil casier %s est déjà présent" % profil_casier.id)
        self.profils_casier[profil_casier.id] = profil_casier

    def ajouter_loi_frottement(self, loi_frottement):
        check_isinstance(loi_frottement, LoiFrottement)
        if loi_frottement.id in self.lois_frottement:
            raise ExceptionCrue10("La loi de frottement %s est déjà présente" % loi_frottement.id)
        self.lois_frottement[loi_frottement.id] = loi_frottement

    def ajouter_lois_frottement_par_defaut(self):
        self.ajouter_loi_frottement(DEFAULT_FK_STO)
        self.ajouter_loi_frottement(DEFAULT_FK_MAX)
        self.ajouter_loi_frottement(DEFAULT_FK_MIN)

    def get_noeud(self, nom_noeud):
        try:
            return self.noeuds[nom_noeud]
        except KeyError:
            raise ExceptionCrue10("Le noeud %s n'est pas dans le %s" % (nom_noeud, self))

    def get_section(self, nom_section):
        try:
            return self.sections[nom_section]
        except KeyError:
            raise ExceptionCrue10("La section %s n'est pas dans le %s" % (nom_section, self))

    def get_branche(self, nom_branche):
        try:
            return self.branches[nom_branche]
        except KeyError:
            raise ExceptionCrue10("La branche %s n'est pas dans le %s" % (nom_branche, self))

    def get_casier(self, nom_casier):
        try:
            return self.casiers[nom_casier]
        except KeyError:
            raise ExceptionCrue10("Le casier %s n'est pas dans le %s" % (nom_casier, self))

    def get_loi_frottement(self, nom_loi_frottement):
        try:
            return self.lois_frottement[nom_loi_frottement]
        except KeyError:
            raise ExceptionCrue10("La loi de frottement %s n'est pas dans le %s" % (nom_loi_frottement, self))

    def get_liste_noeuds(self):
        return [section for _, section in self.noeuds.items()]

    def get_liste_casiers(self):
        return [casier for _, casier in self.casiers.items()]

    def get_liste_sections(self, section_type=None, ignore_inactive=False):
        sections = []
        for _, section in self.sections.items():
            if ignore_inactive and not section.is_active:
                continue
            if section_type is not None:
                if isinstance(section, section_type):
                    sections.append(section)
            else:
                sections.append(section)
        return sections

    def get_liste_sections_profil(self):
        return self.get_liste_sections(section_type=SectionProfil)

    def get_liste_sections_item(self):
        return self.get_liste_sections(section_type=SectionIdem)

    def get_liste_sections_interpolees(self):
        return self.get_liste_sections(section_type=SectionInterpolee)

    def get_liste_sections_sans_geometrie(self):
        return self.get_liste_sections(section_type=SectionSansGeometrie)

    def get_liste_branches(self, filter_branch_types=None):
        branches = []
        for _, branche in self.branches.items():
            if filter_branch_types is not None:
                if branche.type in filter_branch_types:
                    branches.append(branche)
            else:
                branches.append(branche)
        return branches

    def get_liste_lois_frottement(self, ignore_sto=False):
        lois = []
        for _, loi in self.lois_frottement.items():
            if not ignore_sto or loi.type != 'FkSto':
                lois.append(loi)
        return lois

    def _read_dfrt(self):
        """
        Read dfrt.xml file
        """
        root = self._get_xml_root_and_set_comment('dfrt')
        for loi in root.find(PREFIX + 'LoiFFs'):
            loi_frottement = LoiFrottement(loi.get('Nom'), loi.get('Type'),
                                           comment=get_optional_commentaire(loi))
            loi_frottement.set_loi_Fk_values(parse_loi(loi))
            self.ajouter_loi_frottement(loi_frottement)

    def _read_drso(self, filter_branch_types=None):
        """
        Read drso.xml file
        """
        root = self._get_xml_root_and_set_comment('drso')
        for emh_group in root:

            if emh_group.tag == (PREFIX + 'Noeuds'):
                for emh_noeud in emh_group.findall(PREFIX + 'NoeudNiveauContinu'):
                    noeud = Noeud(emh_noeud.get('Nom'))
                    noeud.comment = get_optional_commentaire(emh_noeud)
                    self.ajouter_noeud(noeud)

            elif emh_group.tag == (PREFIX + 'Sections'):

                # SectionProfil, SectionInterpolee, SectionSansGeometrie
                for emh_section in emh_group:
                    section_type = emh_section.tag[len(PREFIX):]
                    nom_section = emh_section.get('Nom')

                    if section_type == 'SectionProfil':
                        section = SectionProfil(nom_section, emh_section.find(PREFIX + 'ProfilSection').get('NomRef'))
                    elif section_type == 'SectionIdem':
                        # Sets temporary to None to preserve order of sections, SectionIdem instance is set below
                        self.sections[nom_section] = None
                        # ajouter_section can not be called in this case, continue statement is mandatory!
                        continue
                    elif section_type == 'SectionInterpolee':
                        section = SectionInterpolee(nom_section)
                    elif section_type == 'SectionSansGeometrie':
                        section = SectionSansGeometrie(nom_section)
                    else:
                        raise NotImplementedError

                    section.comment = get_optional_commentaire(emh_section)
                    self.ajouter_section(section)

                # SectionIdem set after SectionProfil to define its parent section properly
                for emh_section in emh_group:
                    section_type = emh_section.tag[len(PREFIX):]
                    nom_section = emh_section.get('Nom')

                    if section_type == 'SectionIdem':
                        parent_section = self.get_section(emh_section.find(PREFIX + 'Section').get('NomRef'))
                        section = SectionIdem(nom_section, parent_section)
                        section.comment = get_optional_commentaire(emh_section)
                        self.set_section(section)

            elif emh_group.tag == (PREFIX + 'Branches'):
                if filter_branch_types is None:
                    branch_types = list(Branche.TYPES.keys())
                else:
                    branch_types = filter_branch_types

                for emh_branche in emh_group:
                    emh_branche_type = emh_branche.tag[len(PREFIX):]

                    if emh_branche_type == 'BranchePdc':
                        branche_cls = BranchePdC
                    elif emh_branche_type == 'BrancheSeuilTransversal':
                        branche_cls = BrancheSeuilTransversal
                    elif emh_branche_type == 'BrancheSeuilLateral':
                        branche_cls = BrancheSeuilLateral
                    elif emh_branche_type == 'BrancheOrifice':
                        branche_cls = BrancheOrifice
                    elif emh_branche_type == 'BrancheStrickler':
                        branche_cls = BrancheStrickler
                    elif emh_branche_type == 'BrancheNiveauxAssocies':
                        branche_cls = BrancheNiveauxAssocies
                    elif emh_branche_type == 'BrancheBarrageGenerique':
                        branche_cls = BrancheBarrageGenerique
                    elif emh_branche_type == 'BrancheBarrageFilEau':
                        branche_cls = BrancheBarrageFilEau
                    elif emh_branche_type == 'BrancheSaintVenant':
                        branche_cls = BrancheSaintVenant
                    elif emh_branche_type == 'BranchePdc':
                        branche_cls = BranchePdC
                    else:
                        raise ExceptionCrue10("Le type de branche `%s` n'est pas reconnu" % emh_branche_type)

                    branche_type_id = Branche.get_id_type_from_name(emh_branche_type)
                    if branche_type_id in branch_types:
                        # Build branche instance
                        is_active = emh_branche.find(PREFIX + 'IsActive').text == 'true'
                        noeud_amont = self.get_noeud(emh_branche.find(PREFIX + 'NdAm').get('NomRef'))
                        noeud_aval = self.get_noeud(emh_branche.find(PREFIX + 'NdAv').get('NomRef'))
                        branche = branche_cls(emh_branche.get('Nom'), noeud_amont, noeud_aval, is_active)
                        branche.comment = get_optional_commentaire(emh_branche)

                        # Add associated sections
                        if isinstance(branche, BrancheSaintVenant):
                            emh_sections = emh_branche.find(PREFIX + 'BrancheSaintVenant-Sections')
                        else:
                            emh_sections = emh_branche.find(PREFIX + 'Branche-Sections')

                        # Add section pilotage
                        if isinstance(branche, BrancheBarrageGenerique) or isinstance(branche, BrancheBarrageFilEau):
                            branche.section_pilote = \
                                self.get_section(emh_branche.find(PREFIX + 'SectionPilote').get('NomRef'))

                        for emh_section in emh_sections:
                            section = self.get_section(emh_section.get('NomRef'))
                            xp = float(emh_section.find(PREFIX + 'Xp').text)
                            if isinstance(branche, BrancheSaintVenant):
                                section.CoefPond = float(emh_section.find(PREFIX + 'CoefPond').text)
                                section.CoefConv = float(emh_section.find(PREFIX + 'CoefConv').text)
                                section.CoefDiv = float(emh_section.find(PREFIX + 'CoefDiv').text)
                            branche.ajouter_section_dans_branche(section, xp)
                        self.ajouter_branche(branche)

            elif emh_group.tag == (PREFIX + 'Casiers'):
                for emh_profils_casier in emh_group:
                    is_active = emh_profils_casier.find(PREFIX + 'IsActive').text == 'true'
                    noeud = self.get_noeud(emh_profils_casier.find(PREFIX + 'Noeud').get('NomRef'))
                    casier = Casier(emh_profils_casier.get('Nom'), noeud, is_active=is_active)
                    casier.comment = get_optional_commentaire(emh_profils_casier)
                    for emh_pc in emh_profils_casier.findall(PREFIX + 'ProfilCasier'):
                        pc = ProfilCasier(emh_pc.get('NomRef'))
                        self.ajouter_profil_casier(pc)
                        casier.ajouter_profil_casier(pc)
                    self.ajouter_casier(casier)

    def _read_dptg(self):
        """
        Read dptg.xml file
        """
        root = self._get_xml_root_and_set_comment('dptg')
        for emh_group in root:

            if emh_group.tag == (PREFIX + 'DonPrtGeoProfilCasiers'):
                for emh in emh_group.findall(PREFIX + 'ProfilCasier'):
                    nom_profil_casier = emh.get('Nom')
                    profil_casier = self.profils_casier[nom_profil_casier]
                    profil_casier.comment = get_optional_commentaire(emh)
                    profil_casier.set_longueur(float(emh.find(PREFIX + 'Longueur').text))

                    profil_casier.set_xz(parse_loi(emh))

                    lit_num_elt = emh.find(PREFIX + 'LitUtile')
                    profil_casier.xt_min = float(lit_num_elt.find(PREFIX + 'LimDeb').text.split()[0])
                    profil_casier.xt_max = float(lit_num_elt.find(PREFIX + 'LimFin').text.split()[0])

            if emh_group.tag == (PREFIX + 'DonPrtGeoProfilSections'):
                for emh in emh_group.findall(PREFIX + 'ProfilSection'):
                    nom_section = emh.get('Nom').replace('Ps_', 'St_')  # Not necessary consistant
                    section = self.get_section(nom_section)
                    section.comment_profilsection = get_optional_commentaire(emh)

                    fente = emh.find(PREFIX + 'Fente')
                    if fente is not None:
                        section.ajouter_fente(float(fente.find(PREFIX + 'LargeurFente').text),
                                              float(fente.find(PREFIX + 'ProfondeurFente').text))

                    for lit_num_elt in emh.find(PREFIX + 'LitNumerotes').findall(PREFIX + 'LitNumerote'):
                        lit_id = lit_num_elt.find(PREFIX + 'LitNomme').text
                        xt_min = float(lit_num_elt.find(PREFIX + 'LimDeb').text.split()[0])
                        xt_max = float(lit_num_elt.find(PREFIX + 'LimFin').text.split()[0])
                        loi_frottement = self.get_loi_frottement(lit_num_elt.find(PREFIX + 'Frot').get('NomRef'))
                        section.ajouter_lit(LitNumerote(lit_id, xt_min, xt_max, loi_frottement))

                    etiquettes = emh.find(PREFIX + 'Etiquettes')
                    if etiquettes is None:
                        logger.warn("Aucune étiquette trouvée pour %s" % nom_section)
                    else:
                        for etiquette in etiquettes:
                            xt = float(etiquette.find(PREFIX + 'PointFF').text.split()[0])
                            limite = LimiteGeom(etiquette.get('Nom'), xt)
                            section.ajouter_limite_geom(limite)

                    section.set_xz(parse_loi(emh))

            if emh_group.tag == (PREFIX + 'DonPrtGeoSections'):
                for emh in emh_group.findall(PREFIX + 'DonPrtGeoSectionIdem'):
                    self.get_section(emh.get('NomRef')).dz_section_reference = float(emh.find(PREFIX + 'Dz').text)

            if emh_group.tag == (PREFIX + 'DonPrtGeoBranches'):
                for emh in emh_group.findall(PREFIX + 'DonPrtGeoBrancheSaintVenant'):
                    nom_branche = emh.get('NomRef')
                    self.get_branche(nom_branche).CoefSinuo = float(emh.find(PREFIX + 'CoefSinuo').text)

    def _read_dcsp(self):
        root = self._get_xml_root_and_set_comment('dcsp')
        for emh_group in root:

            if emh_group.tag == (PREFIX + 'DonCalcSansPrtBranches'):
                for emh in emh_group:
                    emh_name = emh.get('NomRef')
                    branche = self.branches[emh_name]

                    if emh.tag == PREFIX + 'DonCalcSansPrtBranchePdc':
                        pdc_elt = emh.find(PREFIX + 'Pdc')
                        branche.loi_QPdc = parse_loi(pdc_elt)
                        branche.comment_loi = get_optional_commentaire(pdc_elt)

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheSeuilTransversal':
                        branche.formule_pertes_de_charge = emh.find(PREFIX + 'FormulePdc').text
                        branche.set_liste_elements_seuil(parse_elem_seuil(emh, with_pdc=True))

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheSeuilLateral':
                        branche.formule_pertes_de_charge = emh.find(PREFIX + 'FormulePdc').text
                        branche.set_liste_elements_seuil(parse_elem_seuil(emh, with_pdc=True))

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheOrifice':
                        elem_orifice = emh.find(PREFIX + 'ElemOrifice')
                        branche.CoefCtrLim = float(elem_orifice.find(PREFIX + 'CoefCtrLim').text)
                        branche.Largeur = float(elem_orifice.find(PREFIX + 'Largeur').text)
                        branche.Zseuil = float(elem_orifice.find(PREFIX + 'Zseuil').text)
                        branche.Haut = float(elem_orifice.find(PREFIX + 'Haut').text)
                        branche.CoefD = float(elem_orifice.find(PREFIX + 'CoefD').text)
                        branche.SensOrifice = elem_orifice.find(PREFIX + 'SensOrifice').text

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheNiveauxAssocies':
                        branche.QLimInf = float(emh.find(PREFIX + 'QLimInf').text)
                        branche.QLimSup = float(emh.find(PREFIX + 'QLimSup').text)
                        zasso_elt = emh.find(PREFIX + 'Zasso')
                        branche.loi_ZavZam = parse_loi(zasso_elt)
                        branche.comment_loi = get_optional_commentaire(zasso_elt)

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheBarrageGenerique':
                        branche.QLimInf = float(emh.find(PREFIX + 'QLimInf').text)
                        branche.QLimSup = float(emh.find(PREFIX + 'QLimSup').text)
                        regime_noye_elt = emh.find(PREFIX + 'RegimeNoye')
                        branche.loi_QDz = parse_loi(regime_noye_elt)
                        branche.comment_noye = get_optional_commentaire(regime_noye_elt)
                        regime_denoye_elt = emh.find(PREFIX + 'RegimeDenoye')
                        branche.loi_QpilZam = parse_loi(regime_denoye_elt)
                        branche.comment_denoye = get_optional_commentaire(regime_denoye_elt)

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheBarrageFilEau':
                        branche.QLimInf = float(emh.find(PREFIX + 'QLimInf').text)
                        branche.QLimSup = float(emh.find(PREFIX + 'QLimSup').text)
                        branche.liste_elements_seuil = parse_elem_seuil(emh, with_pdc=False)
                        regime_denoye_elt = emh.find(PREFIX + 'RegimeDenoye')
                        branche.set_loi_QZam(parse_loi(regime_denoye_elt))
                        branche.comment_denoye = get_optional_commentaire(regime_denoye_elt)

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheSaintVenant':
                        branche.CoefBeta = float(emh.find(PREFIX + 'CoefBeta').text)
                        branche.CoefRuis = float(emh.find(PREFIX + 'CoefRuis').text)
                        branche.CoefRuisQdm = float(emh.find(PREFIX + 'CoefRuisQdm').text)

                    else:
                        raise NotImplementedError

    def _read_shp_noeuds(self):
        """Read geometry of all `Noeuds` from current sous_modele (they are compulsory)"""
        geoms = {}
        with fiona.open(self.files['noeuds'], 'r') as src:
            for obj in src:
                nom_noeud = obj['properties']['EMH_NAME']
                coord = obj['geometry']['coordinates'][:2]  # Ignore Z
                geoms[nom_noeud] = Point(coord)
        for _, noeud in self.noeuds.items():
            try:
                noeud.set_geom(geoms[noeud.id])
            except KeyError:
                raise ExceptionCrue10GeometryNotFound(noeud)

    def _read_shp_branches(self):
        """Read geometry of all `Branches` from current sous_modele (they are compulsory)"""
        geoms = {}
        with fiona.open(self.files['branches'], 'r') as src:
            for obj in src:
                nom_branche = obj['properties']['EMH_NAME']
                coords = [coord[:2] for coord in obj['geometry']['coordinates']]  # Ignore Z
                geoms[nom_branche] = LineString(coords)
        for branche in self.get_liste_branches():
            try:
                branche.set_geom(geoms[branche.id])
            except KeyError:
                raise ExceptionCrue10GeometryNotFound(branche)

    def _read_shp_traces_sections(self):
        """
        Read geometry of all `SectionProfils` from current sous_modele
        Missing sections are computed orthogonally to the branch
        """
        geoms = {}
        with fiona.open(self.files['tracesSections'], 'r') as src:
            for obj in src:
                nom_section = obj['properties']['EMH_NAME']
                coords = [coord[:2] for coord in obj['geometry']['coordinates']]  # Ignore Z
                geoms[nom_section] = LineString(coords)
        for section in self.get_liste_sections(section_type=SectionProfil):
            try:
                section.set_geom_trace(geoms[section.id])
            except KeyError:
                branche = self.get_connected_branche(section.id)
                if branche is None:
                    continue  # ignore current orphan section
                section.build_orthogonal_trace(branche.geom)
                logger.warn("La géométrie manquante de la section %s est reconstruite" % section.id)

    def _read_shp_casiers(self):
        """Read geometry of all `Casiers` from current sous_modele (they are compulsory)"""
        geoms = {}
        with fiona.open(self.files['casiers'], 'r') as src:
            for obj in src:
                nom_casier = obj['properties']['EMH_NAME']
                coords = [coord[:2] for coord in obj['geometry']['coordinates']]  # Ignore Z
                geoms[nom_casier] = LinearRing(coords)
        for _, casier in self.casiers.items():
            try:
                casier.set_geom(geoms[casier.id])
            except KeyError:
                raise ExceptionCrue10GeometryNotFound(casier)

    def read_all(self):
        """Lire tous les fichiers du sous-modèle"""
        if not self.was_read:
            # Read xml files
            self._read_dfrt()
            self._read_drso()
            self._read_dptg()
            self._read_dcsp()

            self.set_active_sections()

            # Read shp files
            try:
                if self.noeuds:
                    self._read_shp_noeuds()
                if self.branches:  # Has to be done before sections (to enable orthogonal reconstruction)
                    self._read_shp_branches()
                if self.sections:
                    self._read_shp_traces_sections()
                if self.casiers:
                    self._read_shp_casiers()
            except fiona.errors.DriverError as e:
                logger.warn("Un fichier shp n'a pas pu être lu, la géométrie des EMH n'est pas lisible.")
                logger.warn(str(e))
        self.was_read = True

    def _write_dfrt(self, folder):
        self._write_xml_file(
            'dfrt', folder,
            loi_frottement_liste=[fl for _, fl in self.lois_frottement.items()],
        )

    def _write_drso(self, folder):
        self._write_xml_file(
            'drso', folder,
            noeud_liste=[nd for _, nd in self.noeuds.items()],
            casier_liste=[ca for _, ca in self.casiers.items()],
            section_liste=[st for _, st in self.sections.items()],
            isinstance=isinstance,
            SectionIdem=SectionIdem,
            SectionProfil=SectionProfil,
            SectionSansGeometrie=SectionSansGeometrie,
            SectionInterpolee=SectionInterpolee,
            branche_liste=self.get_liste_branches(),
        )

    def _write_dptg(self, folder):
        self._write_xml_file(
            'dptg', folder,
            profil_casier_list=[pc for _, pc in self.profils_casier.items()],
            section_profil_list=sorted(self.get_liste_sections_profil(), key=lambda st: st.id),  # alphabetic order
            section_idem_list=sorted(self.get_liste_sections_item(), key=lambda st: st.id),  # alphabetic order
            branche_saintvenant_list=sorted(self.get_liste_branches([20]), key=lambda br: br.id),  # alphabetic order
        )

    def _write_dcsp(self, folder):
        self._write_xml_file(
            'dcsp', folder,
            branche_list=self.get_liste_branches(),
            casier_list=[ca for _, ca in self.casiers.items()],
        )

    def _write_shp_noeuds(self, folder):
        schema = {'geometry': 'Point',  # Write Point without 3D not to disturb Fudaa-Crue
                  'properties': OrderedDict([('EMH_NAME', 'str:250'), ('ATTRIBUTE_', 'int:9')])}
        with fiona.open(os.path.join(folder, 'noeuds.shp'), 'w', 'ESRI Shapefile', schema) as layer:
            for i, (_, noeud) in enumerate(self.noeuds.items()):
                if noeud.geom is None:
                    raise ExceptionCrue10GeometryNotFound(noeud)
                point = Point((noeud.geom.x, noeud.geom.y))
                elem = {
                    'geometry': mapping(point),
                    'properties': {'EMH_NAME': noeud.id, 'ATTRIBUTE_': i}
                }
                layer.write(elem)

    def _write_shp_branches(self, folder):
        schema = {'geometry': '3D LineString',
                  'properties': OrderedDict([('EMH_NAME', 'str:250'), ('ATTRIBUTE_', 'int:9')])}
        with fiona.open(os.path.join(folder, 'branches.shp'), 'w', 'ESRI Shapefile', schema) as layer:
            for i, branche in enumerate(self.get_liste_branches()):
                if branche.geom is None:
                    raise ExceptionCrue10GeometryNotFound(branche)
                # Convert LineString to 3D LineString
                line = LineString([(x, y, 0.0) for x, y in branche.geom.coords])
                elem = {
                    'geometry': mapping(line),
                    'properties': {'EMH_NAME': branche.id, 'ATTRIBUTE_': i}
                }
                layer.write(elem)

    def _write_shp_traces_sections(self, folder):
        schema = {'geometry': 'LineString',
                  'properties': OrderedDict([('EMH_NAME', 'str:250'), ('ATTRIBUTE_', 'int:9'),
                                             ('ANGLE_STAR', 'float:32'), ('ANGLE_END', 'float:32')])}
        with fiona.open(os.path.join(folder, 'tracesSections.shp'), 'w', 'ESRI Shapefile', schema) as layer:
            i = 0
            for section in self.get_liste_sections(section_type=SectionProfil):
                if self.get_connected_branche(section.id) is None:
                    continue  # ignore current orphan section
                if section.geom_trace is None:
                    raise ExceptionCrue10GeometryNotFound(section)
                elem = {
                    'geometry': mapping(section.geom_trace),
                    'properties': {'EMH_NAME': section.id, 'ATTRIBUTE_': i,
                                   'ANGLE_STAR': 0.0, 'ANGLE_END': 0.0}
                }
                layer.write(elem)
                i += 0

    def _write_shp_casiers(self, folder):
        schema = {'geometry': '3D LineString',
                  'properties': OrderedDict([('EMH_NAME', 'str:250'), ('ATTRIBUTE_', 'int:9')])}
        with fiona.open(os.path.join(folder, 'casiers.shp'), 'w', 'ESRI Shapefile', schema) as layer:
            for i, (_, casier) in enumerate(self.casiers.items()):
                if casier.geom is None:
                    raise ExceptionCrue10GeometryNotFound(casier)
                # Convert LinearRing to 3D LineString
                line = LineString([(x, y, 0.0) for x, y in casier.geom.coords])
                elem = {
                    'geometry': mapping(line),
                    'properties': {'EMH_NAME': casier.id, 'ATTRIBUTE_': i}
                }
                layer.write(elem)

    def write_all(self, folder, folder_config=None):
        """Écrire tous les fichiers du sous-modèle

        Les fichiers shp sont écrits dans un dossier si `folder_config` est renseigné
        """
        logger.debug("Écriture du %s dans %s" % (self, folder))

        # Create folder if not existing
        if folder_config is not None:
            sm_folder = os.path.join(folder, folder_config, self.id.upper())
            if not os.path.exists(sm_folder):
                os.makedirs(sm_folder)
            if self.noeuds:
                self._write_shp_noeuds(sm_folder)
            if self.branches:
                self._write_shp_branches(sm_folder)
            if self.sections:
                self._write_shp_traces_sections(sm_folder)
            if self.casiers:
                self._write_shp_casiers(sm_folder)

        # Write xml files
        self._write_dfrt(folder)
        self._write_drso(folder)
        self._write_dptg(folder)
        self._write_dcsp(folder)

    def set_section(self, section):
        check_isinstance(section, Section)
        if section.id not in self.sections:
            raise ExceptionCrue10("La section %s n'existe pas" % section.id)
        self.sections[section.id] = section

    def set_active_sections(self):
        """
        Sections are set to active if they are connected to a branch (active or not!)
        """
        for section in self.get_liste_sections():
            section.is_active = False

        for branche in self.get_liste_branches():
            for section in branche.liste_sections_dans_branche:
                section.is_active = branche.is_active

    def replace_zero_xp_sectionaval(self):
        for branche in self.get_liste_branches():
            section_aval = branche.get_section_aval()
            if section_aval.xp <= 0.0:
                section_aval.xp = branche.geom.length

    def get_connected_branche(self, nom_section):
        """
        Returns the connected branche if found, else returns None
        """
        for branche in self.get_liste_branches():
            if nom_section in [section.id for section in branche.liste_sections_dans_branche]:
                return branche
        return None

    def get_connected_branches_in(self, nom_noeud):
        """
        Returns the list of the branches whose downstream node is the requested node
        """
        branches = []
        for branche in self.get_liste_branches():
            if nom_noeud == branche.noeud_aval.id:
                branches.append(branche)
        return branches

    def get_connected_branches_out(self, nom_noeud):
        """
        Returns the list of the branches whose upstream node is the requested node
        """
        branches = []
        for branche in self.get_liste_branches():
            if nom_noeud == branche.noeud_amont.id:
                branches.append(branche)
        return branches

    def get_connected_branches(self, nom_noeud):
        """
        Returns the list of the branches connected to requested node (direction is not considered)
        """
        return self.get_connected_branches_in(nom_noeud) + self.get_connected_branches_out(nom_noeud)

    def get_connected_casier(self, noeud):
        """
        Returns the connected casier if found, else returns None
        """
        for _, casier in self.casiers.items():
            if casier.noeud_reference == noeud:
                return casier
        return None

    def remove_sectioninterpolee(self):
        """Remove all `SectionInterpolee` which are internal sections"""
        for branche in self.get_liste_branches():
            for section in branche.liste_sections_dans_branche[1:-1]:
                if isinstance(section, SectionInterpolee):
                    branche.liste_sections_dans_branche.remove(section)  # remove element (current iteration)
                    self.sections.pop(section.id)
        if len(list(self.get_liste_sections_interpolees())) != 0:
            raise ExceptionCrue10("Des SectionInterpolee n'ont pas pu être supprimées : %s"
                                  % list(self.get_liste_sections_interpolees()))

    @staticmethod
    def are_sections_similar(section1, section2):
        if isinstance(section1, SectionIdem) and isinstance(section2, SectionProfil):
            section_idem = section1
            section_profil = section2
        elif isinstance(section1, SectionProfil) and isinstance(section2, SectionIdem):
            section_idem = section2
            section_profil = section1
        else:
            return False
        return section_idem.section_reference is section_profil and section_idem.dz_section_reference == 0.0

    def is_noeud_supprimable(self, noeud):
        connected_casier = self.get_connected_casier(noeud)
        has_casier = connected_casier is not None

        if not has_casier:
            in_branches = self.get_connected_branches_in(noeud.id)
            out_branches = self.get_connected_branches_out(noeud.id)
            if len(in_branches) == len(out_branches) == 1:
                in_branche = in_branches[0]
                out_branche = out_branches[0]
                in_section = in_branche.get_section_aval()
                out_section = out_branche.get_section_amont()

                if (in_branche.type == out_branche.type == 20) and \
                        (in_branche.is_active == out_branche.is_active) and \
                        self.are_sections_similar(in_section, out_section):
                    return True
        return False

    def supprimer_noeud_entre_deux_branches_fluviales(self, noeud):
        """
        Supprime le noeud du sous-modèle en fusionnant les 2 branches consécutives qui l'entourent
        Attention: comment, CoefSinuo, CoefBeta, CoefRuis, CoefRuisQdm de la branche aval sont ignorés
        :param noeud: noeud à supprimer
        :type noeud: Noeud
        :return Branche: nouvelle branche fusionnée
        """
        # Check that noeud is not connected to a Casier
        connected_casier = self.get_connected_casier(noeud)
        has_casier = connected_casier is not None
        if has_casier:
            raise ExceptionCrue10("Le %s n'est pas supprimable car il est lié à un casier" % noeud)

        # Check upstream (in) and downstream (out) branches and check that they can be merged
        if not self.is_noeud_supprimable(noeud):
            raise ExceptionCrue10("Le %s n'est pas supprimable "
                                  "car il n'est pas entre 2 branches Saint-Venant fusionnables" % noeud)

        # Get upstream (in) and downstream (out) branches and sections at the interface
        in_branche = self.get_connected_branches_in(noeud.id)[0]
        out_branche = self.get_connected_branches_out(noeud.id)[0]
        logger.debug("Suppresion du %s (entre les branches %s et %s)" % (noeud, in_branche.id, out_branche.id))

        in_section = in_branche.get_section_aval()
        out_section = out_branche.get_section_amont()

        in_branche_length = in_branche.get_section_aval().xp
        assert in_branche_length > 0

        if isinstance(out_section, SectionProfil) and isinstance(in_section, SectionIdem):
            # Move SectionProfil in upstream branch
            in_branche.supprimer_section_dans_branche(in_section.id)
            in_branche.ajouter_section_dans_branche(out_section, in_branche_length)

            # Remove orphan SectionIdem
            self.sections.pop(in_section.id)
        else:
            # Remove orphan SectionIdem
            self.sections.pop(out_section.id)

        # Insert sections from downstream to upstream branch
        for section in out_branche.liste_sections_dans_branche[1:]:
            in_branche.ajouter_section_dans_branche(section, in_branche_length + section.xp)
        in_branche.geom = LineString(list(in_branche.geom.coords) + list(out_branche.geom.coords))

        # Merge geometry
        in_branche.noeud_aval = out_branche.noeud_aval

        # Remove old downstream branch and intermediate node
        self.branches.pop(out_branche.id)
        self.noeuds.pop(noeud.id)
        return out_branche

    def convert_sectionidem_to_sectionprofil(self):
        """
        Replace all `SectionIdem` by a `SectionProfil` with an appropriate trace.
        If the SectionIdem is at a branch extremity, which is connected to its original SectionProfil,
           the original SectionProfil is reused. Else the default behaviour is to build a trace which
           is orthogonal to the hydraulic axis.
        """
        for branche in self.get_liste_branches():
            branche.normalize_sections_xp()
            for j, section in enumerate(branche.liste_sections_dans_branche):
                if isinstance(section, SectionIdem):
                    # Find if current SectionIdem is located at geographic position of its original SectionProfil
                    located_at_parent_section = False
                    if j == 0 or j == len(branche.liste_sections_dans_branche) - 1:
                        # Determine node name at junction
                        nom_noeud = branche.noeud_amont.id if j == 0 else branche.noeud_aval.id

                        # Check if any adjacent branches has this section
                        branches = self.get_connected_branches(nom_noeud)
                        branches.remove(branche)
                        for br in branches:
                            section_pos = 0 if br.noeud_amont.id == nom_noeud else -1
                            section_at_node = br.liste_sections_dans_branche[section_pos]
                            if section_at_node is section.section_reference:
                                located_at_parent_section = True
                                break

                    # Replace current instance by its original SectionProfil
                    new_section = section.get_as_sectionprofil()
                    if not located_at_parent_section:
                        # Overwrite SectionProfil original trace by the orthogonal trace because their location differ
                        new_section.build_orthogonal_trace(branche.geom)
                    self.set_section(new_section)
                    branche.liste_sections_dans_branche[j] = new_section

    def normalize_geometry(self):
        for branche in self.get_liste_branches():
            branche.shift_sectionprofil_to_extremity()
        self.convert_sectionidem_to_sectionprofil()

    def ajouter_emh_depuis_sous_modele(self, sous_modele, suffix=''):
        for _, loi_frottement in sous_modele.lois_frottement.items():
            loi_frottement.id = loi_frottement.id + suffix
            self.ajouter_loi_frottement(loi_frottement)
        for _, noeud in sous_modele.noeuds.items():
            self.ajouter_noeud(noeud)
        for _, section in sous_modele.sections.items():
            self.ajouter_section(section)
        for branche in sous_modele.get_liste_branches():
            self.ajouter_branche(branche)
        for _, profils_casier in sous_modele.profils_casier.items():
            self.ajouter_profil_casier(profils_casier)
        for _, casier in sous_modele.casiers.items():
            self.ajouter_casier(casier)

    def validate(self):
        """Check some rules for Crue10"""
        errors = []
        for emh in self.get_liste_noeuds() + self.get_liste_casiers() + self.get_liste_sections() + \
                self.get_liste_branches():
            errors += emh.validate()
        return errors

    def log_validation(self):
        errors = self.validate()
        if errors:
            for nom_emh, message in errors:
                logger.warning('    - %s: %s' % (nom_emh, message))
        else:
            logger.info("=> Pas de problème de validation (pour %s)" % self)

    def summary(self):
        return "%s: %i noeud(s), %i branche(s), %i section(s) (%i profil + %i idem + %i interpolee +" \
               " %i sans géométrie), %i casier(s) (%i profil(s) casier)" % (
                   self, len(self.noeuds), len(self.branches), len(self.sections),
                   len(list(self.get_liste_sections_profil())), len(list(self.get_liste_sections_item())),
                   len(list(self.get_liste_sections_interpolees())), len(list(self.get_liste_sections_sans_geometrie())),
                   len(self.casiers), len(self.profils_casier)
               )

    def __repr__(self):
        return "Sous-modèle %s" % self.id
