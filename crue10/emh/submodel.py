import fiona
import numpy as np
import os.path
from shapely.geometry import LineString, mapping, Point
import xml.etree.ElementTree as ET

from crue10.utils import CrueError, logger, PREFIX

from .branche import Branche
from .noeud import Noeud
from .section import SectionIdem, SectionInterpolee, SectionProfil


class SubModel:
    """
    Crue10 sub-model
    - files <[str]>: dict with path to xml and shp files (keys correspond to `FILES_SHP` and `FILES_XML` lists)
    - noeuds <{crue10.emh.noeud.Noeud}>: nodes
    - sections_profil <{crue10.emh.section.SectionProfil}>
    - sections_idem <{crue10.emh.section.SectionIdem}>
    - sections_interpolee <{crue10.emh.section.SectionInterpolee}>
    - branches <{crue10.emh.section.SectionInterpolee}>: branches (only those with geometry are considered)
    """

    FILES_SHP = ['noeuds', 'branches', 'casiers', 'tracesSections']
    FILES_XML = ['drso', 'dptg', 'dcsp']

    def __init__(self, etu_path, nom_sous_modele):
        """
        :param etu_path: Crue10 study file (etu.xml format)
        :param nom_sous_modele: submodel name
        """
        self.files = {}
        self.noeuds = {}
        self.sections_profil = {}
        self.sections_idem = {}
        self.sections_interpolee = {}
        self.branches = {}
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

    def add_noeud(self, noeud):
        if noeud.id in self.noeuds:
            raise CrueError("Le noeud %s est déjà présent" % noeud.id)
        self.noeuds[noeud.id] = noeud

    def get_section_names(self):
        return list(self.sections_profil.keys()) + list(self.sections_idem.keys()) + \
               list(self.sections_interpolee.keys())

    def add_section_profil(self, section):
        if section.id in self.get_section_names():
            raise CrueError("La SectionProfil `%s` est déjà présente" % section.id)
        self.sections_profil[section.id] = section

    def add_section_idem(self, section):
        if section.id in self.get_section_names():
            raise CrueError("La SectionIdem `%s` est déjà présente" % section.id)
        self.sections_idem[section.id] = section

    def add_section_interpolee(self, section):
        if section.id in self.get_section_names():
            raise CrueError("La SectionInterpolee `%s` est déjà présente" % section.id)
        self.sections_interpolee[section.id] = section

    def get_section(self, section_name):
        try:
            return self.sections_profil[section_name]
        except KeyError:
            try:
                return self.sections_idem[section_name]
            except KeyError:
                return self.sections_interpolee[section_name]

    def add_branche(self, branche):
        if branche.id in self.branches:
            raise CrueError("La branche `%s` est déjà présente" % branche.id)
        self.branches[branche.id] = branche

    def read_drso(self, filter_branch_types=None):
        for emh_group in ET.parse(self.files['drso']).getroot():

            if emh_group.tag == (PREFIX + 'Noeuds'):
                for emh_noeud in emh_group.findall(PREFIX + 'NoeudNiveauContinu'):
                    noeud = Noeud(emh_noeud.get('Nom'))
                    self.add_noeud(noeud)

            elif emh_group.tag == (PREFIX + 'Sections'):
                for emh_section in emh_group.findall(PREFIX + 'SectionProfil'):
                    section_profil = SectionProfil(emh_section.get('Nom'),
                                                   emh_section.find(PREFIX + 'ProfilSection').get('NomRef'))
                    self.add_section_profil(section_profil)

                for emh_section in emh_group.findall(PREFIX + 'SectionIdem'):
                    nom_section = emh_section.get('Nom')
                    section_idem = SectionIdem(nom_section)
                    nom_section_ori = emh_section.find(PREFIX + 'Section').get('NomRef')
                    try:
                        section_idem.section_ori = self.sections_profil[nom_section_ori]
                    except KeyError:
                        raise CrueError("La SectionIdem `%s` fait référence à une SectionProfil inexistante `%s`"
                                        % (nom_section, nom_section_ori))
                    self.add_section_idem(section_idem)

                for emh_section in emh_group.findall(PREFIX + 'SectionInterpolee'):
                    nom_section = emh_section.get('Nom')
                    self.add_section_interpolee(SectionInterpolee(nom_section))

            elif emh_group.tag == (PREFIX + 'Branches'):
                if filter_branch_types is None:
                    branch_types = Branche.TYPES_WITH_GEOM
                else:
                    branch_types = filter_branch_types
                for emh_branche in emh_group:
                    emh_branche_type = emh_branche.tag[len(PREFIX):]
                    branche_type_id = Branche.get_id_type_from_name(emh_branche_type)
                    if branche_type_id not in Branche.TYPES:
                        logger.warn("Le type de branche `%s` n'est pas reconnu" % emh_branche_type)

                    if branche_type_id in branch_types:
                        noeud_amont = self.noeuds[emh_branche.find(PREFIX + 'NdAm').get('NomRef')]
                        noeud_aval = self.noeuds[emh_branche.find(PREFIX + 'NdAv').get('NomRef')]
                        if branche_type_id == 20:
                            emh_sections = emh_branche.find(PREFIX + 'BrancheSaintVenant-Sections')
                        else:
                            emh_sections = emh_branche.find(PREFIX + 'Branche-Sections')
                        branche = Branche(emh_branche.get('Nom'), noeud_amont, noeud_aval, branche_type_id)
                        for emh_section in emh_sections:
                            section = self.get_section(emh_section.get('NomRef'))
                            xp = float(emh_section.find(PREFIX + 'Xp').text)
                            branche.add_section(section, xp)
                        self.add_branche(branche)

    def read_dptg(self):
        """
        Le profil est tronqué sur le lit utile (ie. entre les limites RD et RG)
        """
        for emh_group in ET.parse(self.files['dptg']).getroot():

            if emh_group.tag == (PREFIX + 'DonPrtGeoProfilSections'):
                for emh in emh_group.findall(PREFIX + 'ProfilSection'):
                    nom_section = emh.get('Nom').replace('Ps_', 'St_')  #FIXME: not necessary consistant

                    lits_numerotes = list(emh.find(PREFIX + 'LitNumerotes').findall(PREFIX + 'LitNumerote'))
                    min_xt = float(lits_numerotes[0].find(PREFIX + 'LimDeb').text.split()[0])
                    max_xt = float(lits_numerotes[-1].find(PREFIX + 'LimFin').text.split()[0])

                    etiquette = emh.find(PREFIX + 'Etiquettes').find(PREFIX + 'Etiquette[@Nom="Et_AxeHyd"]')
                    self.sections_profil[nom_section].set_xt_axe(
                        float(etiquette.find(PREFIX + 'PointFF').text.split()[0]))

                    xz = []
                    for pointff in emh.find(PREFIX + 'EvolutionFF').findall(PREFIX + 'PointFF'):
                        x, z = [float(v) for v in pointff.text.split()]
                        if min_xt <= x <= max_xt:
                            xz.append([x, z])
                    self.sections_profil[nom_section].set_xz(np.array(xz))

            if emh_group.tag == (PREFIX + 'DonPrtGeoSections'):
                for emh in emh_group.findall(PREFIX + 'DonPrtGeoSectionIdem'):
                    self.sections_idem[emh.get('NomRef')].dz = float(emh.find(PREFIX + 'Dz').text)

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
                self.sections_profil[nom_section].set_trace(LineString(coords))

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
                raise CrueError("La géométrie de la branche %s n'est pas trouvée!" % (branche.id))

    def read_all(self):
        self.read_drso()
        self.read_dptg()
        # dcsp is ignored
        self.read_shp_noeuds()
        self.read_shp_traces_sections()
        self.read_shp_branches()

    def iter_on_branches(self):
        for _, branche in self.branches.items():
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
                    branche.sections[j] = branche.sections[j].get_as_sectionprofil()
                    self.sections_idem.pop(section.id)
                    self.sections_profil[section.id] = branche.sections[j]

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

    def write_shp_active_trace(self, shp_path):
        schema = {'geometry': 'LineString', 'properties': {'id_section': 'str'}}
        with fiona.open(shp_path, 'w', 'ESRI Shapefile', schema) as out_shp:
            for branche in self.iter_on_branches():
                for section in branche.sections:
                    if isinstance(section, SectionProfil):
                        out_shp.write({'geometry': mapping(section.geom_trace),
                                       'properties': {'id_section': section.id}})

    def __repr__(self):
        return "%i noeuds, %i branches, %i sections (%i profil + %i idem + %i interpolee)" % (
            len(self.noeuds), len(self.branches), len(self.get_section_names()),
            len(self.sections_profil), len(self.sections_idem), len(self.sections_interpolee)
        )
