# coding: utf-8
from collections import OrderedDict
from copy import deepcopy
import fiona
import os.path
from shapely.geometry import LinearRing, LineString, mapping, Point
import xml.etree.ElementTree as ET

from crue10.utils import add_default_missing_metadata, check_preffix, CrueError, CrueErrorGeometryNotFound, \
    JINJA_ENV, PREFIX, XML_ENCODING
from crue10.emh.branche import *
from crue10.emh.casier import Casier, ProfilCasier
from crue10.emh.noeud import Noeud
from crue10.emh.section import DEFAULT_FK_MAX, DEFAULT_FK_MIN, DEFAULT_FK_STO, FrictionLaw, LimiteGeom, LitNumerote, \
    SectionIdem, SectionInterpolee, SectionProfil, SectionSansGeometrie
from mascaret.mascaret_file import Reach, Section
from mascaret.mascaretgeo_file import MascaretGeoFile


def parse_loi(elt, group='EvolutionFF', line='PointFF'):
    elt_group = elt.find(PREFIX + group)
    values = []
    for point_ff in elt_group.findall(PREFIX + line):
        values.append([float(v) for v in point_ff.text.split()])
    return np.array(values)


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


class SubModel:
    """
    Crue10 sub-model
    - id <str>: submodel identifier
    - files <{str}>: dict with path to xml and shp files (keys correspond to `FILES_SHP` and `FILES_XML` lists)
    - metadata <{dict}>: containing metadata (keys correspond to `METADATA_FIELDS` list)
    - noeuds <{crue10.emh.noeud.Noeud}>: nodes
    - sections <{crue10.emh.section.Section}>: sections
        (SectionProfil, SectionIdem, SectionInterpolee or SectionSansGeometrie)
    - branches <{crue10.emh.section.SectionInterpolee}>: branches (only those with geometry are considered)
    - casiers <{crue10.emh.casier.Casier}>: casiers
    - profils_casier <{crue10.emh.casier.ProfilCasier}>: profils casier
    - friction_laws <{crue10.emh.section.FrictionLaw}>: friction laws (Strickler coefficients)
    """

    FILES_SHP = ['noeuds', 'branches', 'casiers', 'tracesSections']
    FILES_XML = ['drso', 'dcsp', 'dptg', 'dfrt']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, submodel_name, access='r', files=None, metadata=None):
        """
        :param submodel_name: submodel name
        :param files: dict with xml and shp path files
        :param metadata: dict containing metadata
        """
        check_preffix(submodel_name, 'Sm_')
        self.id = submodel_name
        self.metadata = {} if metadata is None else metadata
        self.was_read = False

        self.noeuds = OrderedDict()
        self.sections = OrderedDict()
        self.branches = OrderedDict()
        self.casiers = OrderedDict()
        self.profils_casier = OrderedDict()
        self.friction_laws = OrderedDict()

        self.metadata = {'Type': 'Crue10'}
        self.metadata = add_default_missing_metadata(self.metadata, SubModel.METADATA_FIELDS)

        if access == 'r':
            if files is None:
                raise RuntimeError
            if set(files.keys()) != set(SubModel.FILES_XML + SubModel.FILES_SHP):
                raise RuntimeError
            self.files = files
        elif access == 'w':
            self.files = {}
            if files is None:
                for xml_type in SubModel.FILES_XML:
                    self.files[xml_type] = submodel_name[3:] + '.' + xml_type + '.xml'
            else:
                raise RuntimeError

    @property
    def is_active(self):
        return self.metadata['IsActive'] == 'true'

    @property
    def comment(self):
        return self.metadata['Commentaire']

    @property
    def file_basenames(self):
        return {xml_type: os.path.basename(path) for xml_type, path in self.files.items()}

    def add_noeud(self, noeud):
        check_isinstance(noeud, Noeud)
        if noeud.id in self.noeuds:
            raise CrueError("Le noeud %s est déjà présent" % noeud.id)
        self.noeuds[noeud.id] = noeud

    def add_section(self, section):
        check_isinstance(section, [SectionProfil, SectionIdem, SectionSansGeometrie, SectionInterpolee])
        if section.id in self.sections:
            raise CrueError("La Section `%s` est déjà présente" % section.id)
        if isinstance(section, SectionIdem):
            if section.parent_section.id not in self.sections:
                raise CrueError("La SectionIdem `%s` fait référence à une SectionProfil inexistante `%s`"
                                % (section.id, section.section_ori.id))
        if isinstance(section, SectionProfil):
            for lit in section.lits_numerotes:
                if lit.friction_law.id not in self.friction_laws:
                    raise CrueError("La loi de frottement %s de la section `%s` doit être ajoutée au sous-modèle avant"
                                    % (lit.friction_law.id, section.id))
        self.sections[section.id] = section

    def add_branche(self, branche):
        check_isinstance(branche, BRANCHE_CLASSES)
        if branche.id in self.branches:
            raise CrueError("La branche `%s` est déjà présente" % branche.id)
        if branche.noeud_amont.id not in self.noeuds:
            raise CrueError("Le noeud amont %s de la branche `%s` doit être ajouté au sous-modèle avant"
                            % (branche.noeud_amont.id, branche.id))
        if branche.noeud_aval.id not in self.noeuds:
            raise CrueError("Le noeud aval %s de la branche `%s` doit être ajouté au sous-modèle avant"
                            % (branche.noeud_aval.id, branche.id))
        self.branches[branche.id] = branche

    def add_casier(self, casier):
        check_isinstance(casier, Casier)
        if casier.id in self.casiers:
            raise CrueError("Le casier %s est déjà présent" % casier.id)
        if casier.noeud.id not in self.noeuds:
            raise CrueError("Le noeud %s du casier `%s` doit être ajouté au sous-modèle avant"
                            % (casier.noeud.id, casier.id))
        for profilcasier in casier.profils_casier:
            if profilcasier.id not in self.profils_casier:
                self.add_profil_casier(profilcasier)
        self.casiers[casier.id] = casier

    def add_profil_casier(self, profil_casier):
        check_isinstance(profil_casier, ProfilCasier)
        if profil_casier.id in self.profils_casier:
            raise CrueError("Le profil casier %s est déjà présent" % profil_casier.id)
        self.profils_casier[profil_casier.id] = profil_casier

    def add_friction_law(self, friction_law):
        check_isinstance(friction_law, FrictionLaw)
        if friction_law.id in self.friction_laws:
            raise CrueError("La loi de frottement %s est déjà présente" % friction_law.id)
        self.friction_laws[friction_law.id] = friction_law

    def add_default_friction_laws(self):
        self.add_friction_law(DEFAULT_FK_STO)
        self.add_friction_law(DEFAULT_FK_MAX)
        self.add_friction_law(DEFAULT_FK_MIN)

    def rename_emh(self, suffix, emh_list=['Fk', 'Nd', 'Cd', 'St', 'Br']):
        def rename_key_and_obj(dictionary, insert_before_last_split=False):
            """Add suffix to all keys of dictionary and `id` attribute of objects"""
            for old_id in deepcopy(list(dictionary.keys())):
                if insert_before_last_split:
                    new_left_id, new_right_id = old_id.rsplit('_', 1)
                    new_id = new_left_id + suffix + '_' + new_right_id
                else:
                    new_id = old_id + suffix
                dictionary[new_id] = dictionary.pop(old_id)
                dictionary[new_id].id = new_id

        if 'Fk' in emh_list:
            rename_key_and_obj(self.friction_laws)
        if 'Nd' in emh_list:
            rename_key_and_obj(self.noeuds)
        if 'Cd' in emh_list:
            rename_key_and_obj(self.casiers)
            rename_key_and_obj(self.profils_casier, True)
        if 'St' in emh_list:
            rename_key_and_obj(self.sections)
            for st in self.iter_on_sections_profil():
                st.nom_profilsection = st.nom_profilsection + suffix
        if 'Br' in emh_list:
            rename_key_and_obj(self.branches)

    def get_noeud(self, nom_noeud):
        try:
            return self.noeuds[nom_noeud]
        except KeyError:
            raise CrueError("Le noeud %s n'est pas dans le sous-modèle %s" % (nom_noeud, self))

    def iter_on_sections(self, section_type=None, ignore_inactive=False):
        for _, section in self.sections.items():
            if ignore_inactive and not section.is_active:
                continue
            if section_type is not None:
                if isinstance(section, section_type):
                    yield section
            else:
                yield section

    def iter_on_sections_profil(self):
        return self.iter_on_sections(SectionProfil)

    def iter_on_sections_item(self):
        return self.iter_on_sections(SectionIdem)

    def iter_on_sections_interpolees(self):
        return self.iter_on_sections(SectionInterpolee)

    def iter_on_sections_sans_geometrie(self):
        return self.iter_on_sections(SectionSansGeometrie)

    def iter_on_branches(self, filter_branch_types=None):
        for _, branche in self.branches.items():
            if filter_branch_types is not None:
                if branche.type in filter_branch_types:
                    yield branche
            else:
                yield branche

    def _read_dfrt(self):
        """
        Read dfrt.xml file
        """
        for loi in ET.parse(self.files['dfrt']).getroot().find(PREFIX + 'LoiFFs'):
            friction_law = FrictionLaw(loi.get('Nom'), loi.get('Type'), parse_loi(loi))
            self.add_friction_law(friction_law)

    def _read_drso(self, filter_branch_types=None):
        """
        Read drso.xml file
        """
        for emh_group in ET.parse(self.files['drso']).getroot():

            if emh_group.tag == (PREFIX + 'Noeuds'):
                for emh_noeud in emh_group.findall(PREFIX + 'NoeudNiveauContinu'):
                    noeud = Noeud(emh_noeud.get('Nom'))
                    if emh_noeud.find(PREFIX + 'Commentaire') is not None:
                        if emh_noeud.find(PREFIX + 'Commentaire').text is not None:
                            noeud.comment = emh_noeud.find(PREFIX + 'Commentaire').text
                    self.add_noeud(noeud)

            elif emh_group.tag == (PREFIX + 'Sections'):

                # SectionProfil, SectionInterpolee, SectionSansGeometrie
                for emh_section in emh_group:
                    section_type = emh_section.tag[len(PREFIX):]
                    nom_section = emh_section.get('Nom')

                    if section_type == 'SectionProfil':
                        section = SectionProfil(nom_section, emh_section.find(PREFIX + 'ProfilSection').get('NomRef'))
                    elif section_type == 'SectionIdem':
                        continue  # they are considered below
                    elif section_type == 'SectionInterpolee':
                        section = SectionInterpolee(nom_section)
                    elif section_type == 'SectionSansGeometrie':
                        section = SectionSansGeometrie(nom_section)
                    else:
                        raise NotImplementedError

                    if emh_section.find(PREFIX + 'Commentaire') is not None:
                        if emh_section.find(PREFIX + 'Commentaire').text is not None:
                            section.comment = emh_section.find(PREFIX + 'Commentaire').text
                    self.add_section(section)

                # SectionIdem read after SectionProfil to define its parent section
                for emh_section in emh_group:
                    section_type = emh_section.tag[len(PREFIX):]
                    nom_section = emh_section.get('Nom')

                    if section_type == 'SectionIdem':
                        parent_section = self.sections[emh_section.find(PREFIX + 'Section').get('NomRef')]
                        section = SectionIdem(nom_section, parent_section)

                        if emh_section.find(PREFIX + 'Commentaire') is not None:
                            if emh_section.find(PREFIX + 'Commentaire').text is not None:
                                section.comment = emh_section.find(PREFIX + 'Commentaire').text
                        self.add_section(section)

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
                         raise CrueError("Le type de branche `%s` n'est pas reconnu" % emh_branche_type)

                    branche_type_id = Branche.get_id_type_from_name(emh_branche_type)
                    if branche_type_id in branch_types:
                        # Build branche instance
                        is_active = emh_branche.find(PREFIX + 'IsActive').text == 'true'
                        noeud_amont = self.get_noeud(emh_branche.find(PREFIX + 'NdAm').get('NomRef'))
                        noeud_aval = self.get_noeud(emh_branche.find(PREFIX + 'NdAv').get('NomRef'))
                        branche = branche_cls(emh_branche.get('Nom'), noeud_amont, noeud_aval, is_active)
                        if emh_branche.find(PREFIX + 'Commentaire') is not None:
                            if emh_branche.find(PREFIX + 'Commentaire').text is not None:
                                branche.comment = emh_branche.find(PREFIX + 'Commentaire').text

                        # Add associated sections
                        if isinstance(branche, BrancheSaintVenant):
                            emh_sections = emh_branche.find(PREFIX + 'BrancheSaintVenant-Sections')
                        else:
                            emh_sections = emh_branche.find(PREFIX + 'Branche-Sections')

                        # Add section pilotage
                        if isinstance(branche, BrancheBarrageGenerique) or isinstance(branche, BrancheBarrageFilEau):
                            branche.section_pilotage = \
                                self.sections[emh_branche.find(PREFIX + 'SectionPilote').get('NomRef')]

                        for emh_section in emh_sections:
                            section = self.sections[emh_section.get('NomRef')]
                            xp = float(emh_section.find(PREFIX + 'Xp').text)
                            branche.add_section(section, xp)
                        self.add_branche(branche)

            elif emh_group.tag == (PREFIX + 'Casiers'):
                for emh_profils_casier in emh_group:
                    is_active = emh_profils_casier.find(PREFIX + 'IsActive').text == 'true'
                    noeud = self.get_noeud(emh_profils_casier.find(PREFIX + 'Noeud').get('NomRef'))
                    casier = Casier(emh_profils_casier.get('Nom'), noeud, is_active=is_active)
                    if emh_profils_casier.find(PREFIX + 'Commentaire') is not None:
                        if emh_profils_casier.find(PREFIX + 'Commentaire').text is not None:
                            casier.comment = emh_profils_casier.find(PREFIX + 'Commentaire').text
                    for emh_pc in emh_profils_casier.findall(PREFIX + 'ProfilCasier'):
                        pc = ProfilCasier(emh_pc.get('NomRef'))
                        self.add_profil_casier(pc)
                        casier.add_profil_casier(pc)
                    self.add_casier(casier)

    def _read_dptg(self):
        """
        Read dptg.xml file
        FIXME: Le profil est tronqué sur le lit utile (ie. entre les limites RD et RG)
        TODO: Support Fente!
        """
        for emh_group in ET.parse(self.files['dptg']).getroot():

            if emh_group.tag == (PREFIX + 'DonPrtGeoProfilCasiers'):
                for emh in emh_group.findall(PREFIX + 'ProfilCasier'):
                    nom_profil_casier = emh.get('Nom')
                    profil_casier = self.profils_casier[nom_profil_casier]
                    if emh.find(PREFIX + 'Commentaire') is not None:
                        if emh.find(PREFIX + 'Commentaire').text is not None:
                            profil_casier.comment = emh.find(PREFIX + 'Commentaire').text
                    profil_casier.distance = float(emh.find(PREFIX + 'Longueur').text)

                    profil_casier.set_xz(parse_loi(emh))

                    lit_num_elt = emh.find(PREFIX + 'LitUtile')
                    profil_casier.xt_min = float(lit_num_elt.find(PREFIX + 'LimDeb').text.split()[0])
                    profil_casier.xt_max = float(lit_num_elt.find(PREFIX + 'LimFin').text.split()[0])

            if emh_group.tag == (PREFIX + 'DonPrtGeoProfilSections'):
                for emh in emh_group.findall(PREFIX + 'ProfilSection'):
                    nom_section = emh.get('Nom').replace('Ps_', 'St_')  #FIXME: not necessary consistant
                    section = self.sections[nom_section]

                    for lit_num_elt in emh.find(PREFIX + 'LitNumerotes').findall(PREFIX + 'LitNumerote'):
                        lit_id = lit_num_elt.find(PREFIX + 'LitNomme').text
                        xt_min = float(lit_num_elt.find(PREFIX + 'LimDeb').text.split()[0])
                        xt_max = float(lit_num_elt.find(PREFIX + 'LimFin').text.split()[0])
                        friction_law = self.friction_laws[lit_num_elt.find(PREFIX + 'Frot').get('NomRef')]
                        section.add_lit_numerote(LitNumerote(lit_id, xt_min, xt_max, friction_law))
                    section_xt_min = section.lits_numerotes[0].xt_min
                    section_xt_max = section.lits_numerotes[-1].xt_max

                    etiquettes = emh.find(PREFIX + 'Etiquettes')
                    if etiquettes is None:
                        logger.warn("Aucune étiquette trouvée pour %s" % nom_section)
                    else:
                        for etiquette in etiquettes:
                            xt = float(etiquette.find(PREFIX + 'PointFF').text.split()[0])
                            limite = LimiteGeom(etiquette.get('Nom'), xt)
                            section.add_limite_geom(limite)

                    xz = []  # FIXME
                    for pointff in emh.find(PREFIX + 'EvolutionFF').findall(PREFIX + 'PointFF'):
                        x, z = [float(v) for v in pointff.text.split()]
                        if section_xt_min <= x <= section_xt_max:
                            xz.append([x, z])
                    section.set_xz(np.array(xz))

            if emh_group.tag == (PREFIX + 'DonPrtGeoSections'):
                for emh in emh_group.findall(PREFIX + 'DonPrtGeoSectionIdem'):
                    self.sections[emh.get('NomRef')].dz = float(emh.find(PREFIX + 'Dz').text)

            if emh_group.tag == (PREFIX + 'DonPrtGeoBranches'):
                for emh in emh_group.findall(PREFIX + 'DonPrtGeoBrancheSaintVenant'):
                    nom_branche = emh.get('NomRef')
                    self.branches[nom_branche].CoefSinuo = float(emh.find(PREFIX + 'CoefSinuo').text)

    def _read_dcsp(self):
        for emh_group in ET.parse(self.files['dcsp']).getroot():

            if emh_group.tag == (PREFIX + 'DonCalcSansPrtBranches'):
                for emh in emh_group:
                    emh_name = emh.get('NomRef')
                    branche = self.branches[emh_name]

                    if emh.tag == PREFIX + 'DonCalcSansPrtBranchePdc':
                        branche.loi_QPdc = parse_loi(emh.find(PREFIX + 'Pdc'))

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheSeuilTransversal':
                        branche.formule_pdc = emh.find(PREFIX + 'FormulePdc').text
                        branche.elts_seuil = parse_elem_seuil(emh, with_pdc=True)

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheSeuilLateral':
                        branche.formule_pdc = emh.find(PREFIX + 'FormulePdc').text
                        branche.elts_seuil = parse_elem_seuil(emh, with_pdc=True)

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
                        branche.loi_ZavZam = parse_loi(emh.find(PREFIX + 'Zasso'))

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheBarrageGenerique':
                        branche.QLimInf = float(emh.find(PREFIX + 'QLimInf').text)
                        branche.QLimSup = float(emh.find(PREFIX + 'QLimSup').text)
                        branche.loi_QDz = parse_loi(emh.find(PREFIX + 'RegimeNoye'))
                        branche.loi_QpilZam = parse_loi(emh.find(PREFIX + 'RegimeDenoye'))

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheBarrageFilEau':
                        branche.QLimInf = float(emh.find(PREFIX + 'QLimInf').text)
                        branche.QLimSup = float(emh.find(PREFIX + 'QLimSup').text)
                        branche.elts_seuil = parse_elem_seuil(emh, with_pdc=False)
                        branche.loi_QZam = parse_loi(emh.find(PREFIX + 'RegimeDenoye'))

                    elif emh.tag == PREFIX + 'DonCalcSansPrtBrancheSaintVenant':
                        branche.CoefBeta = float(emh.find(PREFIX + 'CoefBeta').text)
                        branche.CoefRuis = float(emh.find(PREFIX + 'CoefRuis').text)
                        branche.CoefRuisQdm = float(emh.find(PREFIX + 'CoefRuisQdm').text)

                    else:
                        raise NotImplementedError

    def _read_shp_noeuds(self):
        with fiona.open(self.files['noeuds'], 'r') as src:
            for obj in src:
                nom_noeud = obj['properties']['EMH_NAME']
                coord = obj['geometry']['coordinates'][:2]  # Ignore Z
                self.noeuds[nom_noeud].set_geom(Point(coord))

    def _read_shp_traces_sections(self):
        with fiona.open(self.files['tracesSections'], 'r') as src:
            for obj in src:
                nom_section = obj['properties']['EMH_NAME']
                coords = [coord[:2] for coord in obj['geometry']['coordinates']]  # Ignore Z
                self.sections[nom_section].set_trace(LineString(coords))

    def _read_shp_branches(self):
        geoms = {}
        with fiona.open(self.files['branches'], 'r') as src:
            for obj in src:
                nom_branche = obj['properties']['EMH_NAME']
                coords = [coord[:2] for coord in obj['geometry']['coordinates']]  # Ignore Z
                geoms[nom_branche] = LineString(coords)
        for branche in self.iter_on_branches():
            try:
                branche.set_geom(geoms[branche.id])
            except KeyError:
                raise CrueError("La géométrie de la branche %s n'est pas trouvée!" % branche.id)

    def _read_shp_casiers(self):
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
                raise CrueError("La géométrie du casier %s n'est pas trouvée!" % casier.id)

    def read_all(self):
        if not self.was_read:
            # Read xml files
            self._read_dfrt()
            self._read_drso()
            self._read_dptg()
            self._read_dcsp()

            # Read shp files
            try:
                if self.noeuds:
                    self._read_shp_noeuds()
                if self.sections:
                    self._read_shp_traces_sections()
                if self.branches:
                    self._read_shp_branches()
                if self.casiers:
                    self._read_shp_casiers()
            except fiona.errors.DriverError as e:
                logger.warn("Un fichier shp n'a pas pu être lu, la géométrie des EMH n'est pas lisible.")
                logger.warn(str(e))
        self.was_read = True

        self.set_active_sections()

    def _write_dfrt(self, folder):
        xml = 'dfrt'
        template_render = JINJA_ENV.get_template(xml + '.xml').render(
            comment=self.comment,
            friction_law_list=[fl for _, fl in self.friction_laws.items()],
        )
        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

    def _write_drso(self, folder):
        xml = 'drso'
        template_render = JINJA_ENV.get_template(xml + '.xml').render(
            comment=self.comment,
            noeud_list=[nd for _, nd in self.noeuds.items()],
            casier_list=[ca for _, ca in self.casiers.items()],
            section_list=[st for _, st in self.sections.items()],
            isinstance=isinstance,
            SectionIdem=SectionIdem,
            SectionProfil=SectionProfil,
            SectionSansGeometrie=SectionSansGeometrie,
            SectionInterpolee=SectionInterpolee,
            branche_list=self.iter_on_branches(),
        )
        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

    def _write_dptg(self, folder):
        xml = 'dptg'
        template_render = JINJA_ENV.get_template(xml + '.xml').render(
            comment=self.comment,
            profil_casier_list=[pc for _, pc in self.profils_casier.items()],
            section_profil_list=sorted(self.iter_on_sections_profil(), key=lambda st: st.id),  # alphabetic order
            section_idem_list=sorted(self.iter_on_sections_item(), key=lambda st: st.id),  # alphabetic order
            branche_saintvenant_list=sorted(self.iter_on_branches([20]), key=lambda br: br.id),  # alphabetic order
        )
        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

    def _write_dcsp(self, folder):
        xml = 'dcsp'
        template_render = JINJA_ENV.get_template(xml + '.xml').render(
            comment=self.comment,
            branche_list=self.iter_on_branches(),
            casier_list=[ca for _, ca in self.casiers.items()],
        )
        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

    def _write_shp_noeuds(self, folder):
        schema = {'geometry': 'Point',  # Write Point without 3D not to disturb Fudaa-Crue
                  'properties': OrderedDict([('EMH_NAME', 'str:250'), ('ATTRIBUTE_', 'int:9')])}
        with fiona.open(os.path.join(folder, 'noeuds.shp'), 'w', 'ESRI Shapefile', schema) as layer:
            for i, (_, noeud) in enumerate(self.noeuds.items()):
                if noeud.geom is None:
                    raise CrueErrorGeometryNotFound(noeud)
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
            for i, branche in enumerate(self.iter_on_branches()):
                if branche.geom is None:
                    raise CrueErrorGeometryNotFound(branche)
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
            for section in self.iter_on_sections_profil():
                if section.is_active:
                    if section.geom_trace is None:  # Try to rebuild a theoretical geometry (it may crash easily!)
                        branche = self.get_connected_branche(section.id)
                        if branche is None:
                            raise RuntimeError
                        section.build_orthogonal_trace(branche.geom)
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
                    raise CrueErrorGeometryNotFound(casier)
                # Convert LinearRing to 3D LineString
                line = LineString([(x, y, 0.0) for x, y in casier.geom.coords])
                elem = {
                    'geometry': mapping(line),
                    'properties': {'EMH_NAME': casier.id, 'ATTRIBUTE_': i}
                }
                layer.write(elem)

    def write_all(self, folder, folder_config):
        logger.debug("Writing %s in %s" % (self, folder))

        # TO CHECK
        # Casier has at least one ProfilCasier

        # Create folder if not existing
        sm_folder = os.path.join(folder, folder_config, self.id.upper())
        if folder:
            if not os.path.exists(sm_folder):
                os.makedirs(sm_folder)

        # Write xml files
        self._write_dfrt(folder)
        self._write_drso(folder)
        self._write_dptg(folder)
        self._write_dcsp(folder)

        if self.noeuds:
            self._write_shp_noeuds(sm_folder)
        if self.branches:
            self._write_shp_branches(sm_folder)
        if self.sections:
            self._write_shp_traces_sections(sm_folder)
        if self.casiers:
            self._write_shp_casiers(sm_folder)

    def write_shp_limites_lits_numerotes(self, shp_path):
        schema = {'geometry': 'LineString', 'properties': {'id_limite': 'str', 'id_branche': 'str'}}
        with fiona.open(shp_path, 'w', 'ESRI Shapefile', schema) as out_shp:
            for branche in self.iter_on_branches():
                for i_lit, lit_name in enumerate(LitNumerote.LIMIT_NAMES):
                    coords = []
                    for section in branche.sections:
                        if isinstance(section, SectionProfil):
                            if i_lit == 0:
                                point = section.interp_point(section.lits_numerotes[0].xt_min)
                            else:
                                point = section.interp_point(section.lits_numerotes[i_lit - 1].xt_max)
                            coords.append((point.x, point.y))
                    if len(coords) > 2:
                        out_shp.write({'geometry': mapping(LineString(coords)),
                                       'properties': {'id_limite': lit_name, 'id_branche': branche.id}})

    def write_mascaret_geometry(self, geo_path):
        """
        @brief: Convert submodel to mascaret geometry format (georef for example)
        Only reaches with sections having elevation information are written
        TODO: Add min/maj delimiter
        @param geo_path <str>: output file path
        """
        geofile = MascaretGeoFile(geo_path, access='w')
        i_section = 0
        for i_branche, branche in enumerate(self.iter_on_branches()):
            if branche.has_geom():
                reach = Reach(i_branche, name=branche.id)
                for section in branche.sections:
                    if not isinstance(section, SectionProfil):
                        raise CrueError("The ``%s, which is not a SectionProfil, could not be written" % section)
                    masc_section = Section(i_section, section.xp, name=section.id)
                    coord = np.array(section.get_coord(add_z=True))
                    masc_section.set_points_from_xyz(coord[:, 0], coord[:, 1], coord[:, 2])
                    pt_at_axis = section.interp_point(section.xt_axe)
                    masc_section.axis = (pt_at_axis.x, pt_at_axis.y)
                    reach.add_section(masc_section)
                    i_section += 1
                geofile.add_reach(reach)
        geofile.save()

    def set_active_sections(self):
        """
        Sections are set to active if they are connected to a branch
        """
        for section in self.iter_on_sections():
            section.is_active = False

        for branche in self.iter_on_branches():
            for section in branche.sections:
                section.is_active = True

    def get_connected_branche(self, nom_section):
        """
        Returns the connected branche if found, else returns None
        """
        for branche in self.iter_on_branches():
            if nom_section in [section.id for section in branche.sections]:
                return branche
        return None

    def get_connected_branches(self, nom_noeud):
        """
        Returns the list of the branches connected to requested node
        """
        branches = []
        for branche in self.iter_on_branches():
            if nom_noeud in (branche.noeud_amont.id, branche.noeud_aval.id):
                branches.append(branche)
        return branches

    def get_connected_casier(self, noeud):
        """
        Returns the connected casier if found, else returns None
        """
        for _, casier in self.casiers.items():
            if casier.noeud == noeud:
                return casier
        return None

    def remove_sectioninterpolee(self):
        """Remove all `SectionInterpolee` which are internal sections"""
        for branche in self.iter_on_branches():
            for section in branche.sections[1:-1]:
                if isinstance(section, SectionInterpolee):
                    branche.sections.remove(section)  # remove element (current iteration)
                    self.sections.pop(section.id)
        if len(list(self.iter_on_sections_interpolees())) != 0:
            raise CrueError("Des SectionInterpolee n'ont pas pu être supprimées : %s"
                            % list(self.iter_on_sections_interpolees()))

    def convert_sectionidem_to_sectionprofil(self):
        """
        Replace all `SectionIdem` by a `SectionProfil` with an appropriate trace.
        If the SectionIdem is at a branch extremity, which is connected to its original SectionProfil,
           the original SectionProfil is reused. Else the default behaviour is to build a trace which
           is orthogonal to the hydraulic axis.
        """
        for branche in self.iter_on_branches():
            branche.normalize_sections_xp()
            for j, section in enumerate(branche.sections):
                if isinstance(section, SectionIdem):
                    # Replace current instance by its original SectionProfil
                    new_section = section.get_as_sectionprofil()
                    branche.sections[j] = new_section
                    self.sections[section.id] = new_section

                    # Find if current SectionIdem is located at geographic position of its original SectionProfil
                    located_at_parent_section = False
                    if j == 0 or j == len(branche.sections) - 1:
                        # Determine node name at junction
                        nom_noeud = branche.noeud_amont.id if j == 0 else branche.noeud_aval.id

                        # Check if any adjacent branches has this section
                        branches = self.get_connected_branches(nom_noeud)
                        branches.remove(branche)
                        for br in branches:
                            section_pos = 0 if br.noeud_amont.id == nom_noeud else -1
                            section_at_node = br.sections[section_pos]
                            if section_at_node is section.parent_section:
                                located_at_parent_section = True
                                break
                    if not located_at_parent_section:
                        # Overwrite SectionProfil original trace by the orthogonal trace because their location differ
                        branche.sections[j].build_orthogonal_trace(branche.geom)

    def normalize_geometry(self):
        for branche in self.iter_on_branches():
            branche.shift_sectionprofil_to_extremity()
        self.convert_sectionidem_to_sectionprofil()

    def add_emh_from_submodel(self, submodel, suffix=''):
        for _, friction_law in submodel.friction_laws.items():
            friction_law.id = friction_law.id + suffix
            self.add_friction_law(friction_law)
        for _, noeud in submodel.noeuds.items():
            self.add_noeud(noeud)
        for _, section in submodel.sections.items():
            self.add_section(section)
        for branche in submodel.iter_on_branches():
            self.add_branche(branche)
        for _, profils_casier in submodel.profils_casier.items():
            self.add_profil_casier(profils_casier)
        for _, casier in submodel.casiers.items():
            self.add_casier(casier)

    def summary(self):
        return "%s: %i noeud(s), %i branche(s), %i section(s) (%i profil + %i idem + %i interpolee +" \
               " %i sans géométrie), %i casier(s) (%i profil(s) casier)" % (
           self, len(self.noeuds), len(self.branches), len(self.sections),
           len(list(self.iter_on_sections_profil())), len(list(self.iter_on_sections_item())),
           len(list(self.iter_on_sections_interpolees())), len(list(self.iter_on_sections_sans_geometrie())),
           len(self.casiers), len(self.profils_casier)
        )

    def __repr__(self):
        return "Sous-modèle %s" % self.id
