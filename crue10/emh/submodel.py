from collections import OrderedDict
import fiona
from jinja2 import Environment, FileSystemLoader
import os.path
from shapely.geometry import LineString, mapping
import xml.etree.ElementTree as ET

from crue10.utils import CrueError, PREFIX
from mascaret.mascaret_file import Reach, Section
from mascaret.mascaretgeo_file import MascaretGeoFile

from .branche import *
from .casier import Casier, ProfilCasier
from .noeud import Noeud
from .section import FrictionLaw, LimiteGeom, LitNumerote, SectionIdem, SectionInterpolee, \
    SectionProfil, SectionSansGeometrie


XML_ENCODING = 'utf-8'


class SubModel:
    """
    Crue10 sub-model
    - files <[str]>: dict with path to xml and shp files (keys correspond to `FILES_SHP` and `FILES_XML` lists)
    - noeuds <{crue10.emh.noeud.Noeud}>: nodes
    - sections <{crue10.emh.section.Section}>: sections
        (SectionProfil, SectionIdem, SectionInterpolee or SectionSansGeometrie)
    - branches <{crue10.emh.section.SectionInterpolee}>: branches (only those with geometry are considered)
    - casiers <{crue10.emh.casier.Casier}>: casiers
    - profils_casier <{crue10.emh.casier.ProfilCasier}>: profils casier
    - friction_laws <{crue10.emh.section.FrictionLaw}>: friction laws (Strickler coefficients)
    """

    FILES_SHP = ['noeuds', 'branches', 'casiers', 'tracesSections']
    FILES_XML = ['dfrt', 'drso', 'dptg', 'dcsp']

    def __init__(self, etu_path, nom_sous_modele):
        """
        :param etu_path: Crue10 study file (etu.xml format)
        :param nom_sous_modele: submodel name
        """
        self.submodel_name = nom_sous_modele
        self.files = {}
        self.noeuds = OrderedDict()
        self.sections = OrderedDict()
        self.branches = OrderedDict()
        self.casiers = OrderedDict()
        self.profils_casier = OrderedDict()
        self.friction_laws = OrderedDict()
        self._get_xml_files(etu_path, nom_sous_modele)
        self._get_shp_files(etu_path, nom_sous_modele)

    def _get_xml_files(self, etu_path, nom_sous_modele):
        sous_modeles = ET.parse(etu_path).getroot().find(PREFIX + 'SousModeles')
        sous_modele = sous_modeles.find(PREFIX + 'SousModele[@Nom="%s"]' % nom_sous_modele)
        if sous_modele is None:
            raise CrueError("Le sous-modèle %s n'existe pas !\n" % nom_sous_modele +
                            "Les sous-modeles possibles sont :\n%s" % [sm.attrib['Nom'] for sm in sous_modeles])
        sm_name = sous_modele.attrib['Nom']
        if sm_name == nom_sous_modele:
            fichiers = sous_modele.find(PREFIX + 'SousModele-FichEtudes')
            for ext in SubModel.FILES_XML:
                try:
                    filename = fichiers.find(PREFIX + ext.upper()).attrib['NomRef']
                except AttributeError:
                    raise CrueError("Le fichier %s n'est pas renseigné dans le sous-modèle." % ext)
                if filename is None:
                    raise CrueError("Le sous-modèle n'a pas de fichier %s !" % ext)
                self.files[ext] = os.path.join(os.path.dirname(etu_path), filename)

    def _get_shp_files(self, etu_path, nom_sous_modele):
        for shp_name in SubModel.FILES_SHP:
            self.files[shp_name] = os.path.join(os.path.dirname(etu_path), 'Config', nom_sous_modele.upper(),
                                                shp_name + '.shp')

    def add_friction_law(self, friction_law):
        if friction_law.id in self.friction_laws:
            raise CrueError("La loi de frottement %s est déjà présente" % friction_law.id)
        self.friction_laws[friction_law.id] = friction_law

    def add_noeud(self, noeud):
        if noeud.id in self.noeuds:
            raise CrueError("Le noeud %s est déjà présent" % noeud.id)
        self.noeuds[noeud.id] = noeud

    def get_active_section_names(self):
        """Returns the list of all active section names"""
        for _, section in self.sections.items():
            if section.is_active:
                yield section.id

    def add_section(self, section):
        if section.id in self.sections:
            raise CrueError("La Section `%s` est déjà présente" % section.id)
        self.sections[section.id] = section

    def add_branche(self, branche):
        if branche.id in self.branches:
            raise CrueError("La branche `%s` est déjà présente" % branche.id)
        self.branches[branche.id] = branche

    def add_casier(self, casier):
        if casier.id in self.casiers:
            raise CrueError("Le casier %s est déjà présent" % casier.id)
        self.casiers[casier.id] = casier

    def add_profil_casier(self, profil_casier):
        if profil_casier.id in self.profils_casier:
            raise CrueError("Le profil casier %s est déjà présent" % profil_casier.id)
        self.profils_casier[profil_casier.id] = profil_casier

    def read_dfrt(self):
        """
        Read dfrt.xml file
        """
        for loi in ET.parse(self.files['dfrt']).getroot().find(PREFIX + 'LoiFFs'):
            xk_list = []
            for xk in loi.find(PREFIX + 'EvolutionFF'):
                xk_list.append(tuple(float(x) for x in xk.text.split()))
            friction_law = FrictionLaw(loi.get('Nom'), loi.get('Type'), np.array(xk_list))
            self.add_friction_law(friction_law)

    def read_drso(self, filter_branch_types=None):
        """
        Read drso.xml file
        """
        for emh_group in ET.parse(self.files['drso']).getroot():

            if emh_group.tag == (PREFIX + 'Noeuds'):
                for emh_noeud in emh_group.findall(PREFIX + 'NoeudNiveauContinu'):
                    noeud = Noeud(emh_noeud.get('Nom'))
                    if emh_noeud.find(PREFIX + 'Commentaire').text is not None:
                        noeud.comment = emh_noeud.find(PREFIX + 'Commentaire').text
                    self.add_noeud(noeud)

            elif emh_group.tag == (PREFIX + 'Sections'):

                for emh_section in emh_group:
                    section_type = emh_section.tag[len(PREFIX):]
                    nom_section = emh_section.get('Nom')

                    if section_type == 'SectionProfil':
                        section = SectionProfil(nom_section, emh_section.find(PREFIX + 'ProfilSection').get('NomRef'))
                    elif section_type == 'SectionIdem':
                        section = SectionIdem(nom_section)
                        section.section_ori = emh_section.find(PREFIX + 'Section').get('NomRef')
                    elif section_type == 'SectionInterpolee':
                        section = SectionInterpolee(nom_section)
                    elif section_type == 'SectionSansGeometrie':
                        section = SectionSansGeometrie(nom_section)
                    else:
                        raise NotImplementedError
                    if emh_section.find(PREFIX + 'Commentaire').text is not None:
                        section.comment = emh_section.find(PREFIX + 'Commentaire').text
                    self.add_section(section)

                # Replace SectionIdem.section_ori and check consistancy
                for section in self.iter_on_sections_item():
                    try:
                        section.section_ori = self.sections[section.section_ori]
                    except KeyError:
                        raise CrueError("La SectionIdem `%s` fait référence à une Section inexistante `%s`"
                                        % (section, section.section_ori))
                    if not isinstance(section.section_ori, SectionProfil):
                        raise CrueError("La SectionIdem `%s` ne fait pas référence à une SectionProfil"
                                        % section)

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
                        noeud_amont = self.noeuds[emh_branche.find(PREFIX + 'NdAm').get('NomRef')]
                        noeud_aval = self.noeuds[emh_branche.find(PREFIX + 'NdAv').get('NomRef')]
                        branche = branche_cls(emh_branche.get('Nom'), noeud_amont, noeud_aval, is_active)
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
                    nom_noeud = emh_profils_casier.find(PREFIX + 'Noeud').get('NomRef')
                    casier = Casier(emh_profils_casier.get('Nom'), nom_noeud, is_active=is_active)
                    if emh_profils_casier.find(PREFIX + 'Commentaire').text is not None:
                        casier.comment = emh_profils_casier.find(PREFIX + 'Commentaire').text
                    for emh_pc in emh_profils_casier.findall(PREFIX + 'ProfilCasier'):
                        pc = ProfilCasier(emh_pc.get('NomRef'))
                        self.add_profil_casier(pc)
                        casier.add_profil_casier(pc)
                    self.add_casier(casier)

    def read_dptg(self):
        """
        Read dptg.xml file
        /!\ Le profil est tronqué sur le lit utile (ie. entre les limites RD et RG)
        """
        for emh_group in ET.parse(self.files['dptg']).getroot():

            if emh_group.tag == (PREFIX + 'DonPrtGeoProfilCasiers'):
                for emh in emh_group.findall(PREFIX + 'ProfilCasier'):
                    nom_profil_casier = emh.get('Nom')
                    profil_casier = self.profils_casier[nom_profil_casier]
                    if emh.find(PREFIX + 'Commentaire').text is not None:
                        profil_casier.comment = emh.find(PREFIX + 'Commentaire').text
                    profil_casier.distance = float(emh.find(PREFIX + 'Longueur').text)

                    lit_num_elt = emh.find(PREFIX + 'LitUtile')
                    profil_casier.xt_min = float(lit_num_elt.find(PREFIX + 'LimDeb').text.split()[0])
                    profil_casier.xt_max = float(lit_num_elt.find(PREFIX + 'LimFin').text.split()[0])

                    xz = []
                    for pointff in emh.find(PREFIX + 'EvolutionFF').findall(PREFIX + 'PointFF'):
                        xz.append([float(v) for v in pointff.text.split()])
                    profil_casier.set_xz(np.array(xz))

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

                    for etiquette in emh.find(PREFIX + 'Etiquettes'):
                        xt = float(etiquette.find(PREFIX + 'PointFF').text.split()[0])
                        limite = LimiteGeom(etiquette.get('Nom'), xt)
                        section.add_limite_geom(limite)

                    xz = []
                    for pointff in emh.find(PREFIX + 'EvolutionFF').findall(PREFIX + 'PointFF'):
                        x, z = [float(v) for v in pointff.text.split()]
                        if section_xt_min <= x <= section_xt_max:
                            xz.append([x, z])
                    section.set_xz(np.array(xz))

            if emh_group.tag == (PREFIX + 'DonPrtGeoSections'):
                for emh in emh_group.findall(PREFIX + 'DonPrtGeoSectionIdem'):
                    self.sections[emh.get('NomRef')].dz = float(emh.find(PREFIX + 'Dz').text)


    def read_shp_noeuds(self):
        with fiona.open(self.files['noeuds'], 'r') as src:
            for obj in src:
                nom_noeud = obj['properties']['EMH_NAME']
                coord = obj['geometry']['coordinates']
                self.noeuds[nom_noeud].set_geom(Point(coord))

    def read_shp_traces_sections(self):
        with fiona.open(self.files['tracesSections'], 'r') as src:
            for obj in src:
                nom_section = obj['properties']['EMH_NAME']
                coords = obj['geometry']['coordinates']
                self.sections[nom_section].set_trace(LineString(coords))

    def read_shp_branches(self):
        geoms = {}
        with fiona.open(self.files['branches'], 'r') as src:
            for obj in src:
                nom_branche = obj['properties']['EMH_NAME']
                coords = obj['geometry']['coordinates']
                geoms[nom_branche] = LineString(coords)
        for branche in self.iter_on_branches():
            try:
                branche.set_geom(geoms[branche.id])
            except KeyError:
                raise CrueError("La géométrie de la branche %s n'est pas trouvée!" % branche.id)

    def read_shp_casiers(self):
        geoms = {}
        with fiona.open(self.files['casiers'], 'r') as src:
            for obj in src:
                nom_casier = obj['properties']['EMH_NAME']
                coords = obj['geometry']['coordinates']
                geoms[nom_casier] = LineString(coords)
        for _, casier in self.casiers.items():
            try:
                casier.set_geom(geoms[casier.id])
            except KeyError:
                raise CrueError("La géométrie du casier %s n'est pas trouvée!" % casier.id)

    def iter_on_sections(self, section_type=None):
        for _, section in self.sections.items():
            if type is not None:
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

    def set_active_sections(self):
        for branche in self.iter_on_branches():
            branch_is_active = branche.is_active
            for section in branche.sections:
                section.is_active = branch_is_active

    def read_all(self):
        self.read_dfrt()
        self.read_drso()
        self.read_dptg()
        # dcsp is ignored
        self.read_shp_noeuds()
        self.read_shp_traces_sections()
        self.read_shp_branches()
        if self.casiers:
            self.read_shp_casiers()
        self.set_active_sections()

    def iter_on_branches(self, filter_branch_types=None):
        for _, branche in self.branches.items():
            if filter_branch_types is not None:
                if branche.type in filter_branch_types:
                    yield branche
            else:
                yield branche

    def connected_branches(self, nom_noeud):
        """
        Returns the list of the branches connected to requested node
        """
        branches = []
        for branche in self.iter_on_branches():
            if nom_noeud in (branche.noeud_amont.id, branche.noeud_aval.id):
                branches.append(branche)
        return branches

    def remove_sectioninterpolee(self):
        """Remove all `SectionInterpolee` which are internal sections"""
        for branche in self.iter_on_branches():
            for section in branche.sections[1:-1]:
                if isinstance(section, SectionInterpolee):
                    branche.sections.remove(section)  # remove element (current iteration)
                    self.sections_interpolee.pop(section.id)
        if self.sections_interpolee:
            raise CrueError("Des SectionInterpolee n'ont pas pu être supprimées : %s"
                            % list(self.sections_interpolee.keys()))

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
                    located_at_section_ori = False
                    if j == 0 or j == len(branche.sections) - 1:
                        # Determine node name at junction
                        nom_noeud = branche.noeud_amont.id if j == 0 else branche.noeud_aval.id

                        # Check if any adjacent branches has this section
                        branches = self.connected_branches(nom_noeud)
                        branches.remove(branche)
                        for br in branches:
                            section_pos = 0 if br.noeud_amont.id == nom_noeud else -1
                            section_at_node = br.sections[section_pos]
                            if section_at_node is section.section_ori:
                                located_at_section_ori = True
                                break
                    if not located_at_section_ori:
                        # Overwrite SectionProfil original trace by the orthogonal trace because their location differ
                        branche.sections[j].build_orthogonal_trace(branche.geom)

    def normalize_geometry(self):
        for branche in self.iter_on_branches():
            branche.shift_sectionprofil_to_extremity()
        self.convert_sectionidem_to_sectionprofil()

    def write_shp_active_trace(self, shp_path):
        schema = {'geometry': 'LineString', 'properties': {'id_section': 'str'}}
        with fiona.open(shp_path, 'w', 'ESRI Shapefile', schema) as out_shp:
            for branche in self.iter_on_branches():
                for section in branche.sections:
                    if isinstance(section, SectionProfil):
                        out_shp.write({'geometry': mapping(section.geom_trace),
                                       'properties': {'id_section': section.id}})

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

    def convert_to_mascaret_format(self, geo_path):
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

    def get_missing_active_sections(self, section_id_list):
        """
        Returns the list of the requested sections which are not found (or not active) in the current submodel
            (section type is not checked)
        :param section_id_list: list of section identifiers
        """
        return set(self.get_active_section_names()).difference(set(section_id_list))

    def export_xml(self, folder):
        env = Environment(loader=FileSystemLoader(os.path.join('crue10', 'templates')))

        xml = 'dfrt'
        template = env.get_template(xml + '.xml')
        template_render = template.render(
            friction_law_list=[fl for _, fl in self.friction_laws.items()],
        )
        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

        xml = 'drso'
        template = env.get_template(xml + '.xml')
        template_render = template.render(
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

        xml = 'dptg'
        template = env.get_template(xml + '.xml')
        template_render = template.render(
            profil_casier_list=[pc for _, pc in self.profils_casier.items()],
            section_profil_list=sorted(self.iter_on_sections_profil(), key=lambda st: st.id),  # alphabetic order
            section_idem_list=sorted(self.iter_on_sections_item(), key=lambda st: st.id),  # alphabetic order
            branche_saintvenant_list=sorted(self.iter_on_branches([20]), key=lambda br: br.id),  # alphabetic order
        )
        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

        xml = 'dcsp'
        template = env.get_template(xml + '.xml')
        template_render = template.render(
            branche_list=self.iter_on_branches(),
            casier_list=[ca for _, ca in self.casiers.items()],
        )
        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

    def __repr__(self):
        return "%i noeuds, %i branches, %i sections (%i profil + %i idem + %i interpolee + %i sans géométrie), " \
           "%i casiers (%i profils casier)" % (
           len(self.noeuds), len(self.branches), len(self.sections),
           len(list(self.iter_on_sections_profil())), len(list(self.iter_on_sections_item())),
           len(list(self.iter_on_sections_interpolees())), len(list(self.iter_on_sections_sans_geometrie())),
           len(self.casiers), len(self.profils_casier)
        )
