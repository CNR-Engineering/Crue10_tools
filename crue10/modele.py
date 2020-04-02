# coding: utf-8
from builtins import super  # Python2 fix
from collections import Counter, OrderedDict
from copy import deepcopy
import fiona
from lxml import etree
import numpy as np
import os.path
from shapely.geometry import LineString, mapping, Point

from crue10.base import FichierXML
from crue10.emh.branche import BrancheOrifice, BrancheBarrageFilEau, BrancheBarrageGenerique
from crue10.emh.section import SectionProfil, LitNumerote
from crue10.utils import check_isinstance, check_preffix, duration_iso8601_to_seconds, duration_seconds_to_iso8601, \
    ExceptionCrue10, logger, PREFIX, write_default_xml_file, write_xml_from_tree
from crue10.utils.graph_1d_model import *
from crue10.sous_modele import SousModele
from mascaret.mascaret_file import Reach, Section
from mascaret.mascaretgeo_file import MascaretGeoFile


class Modele(FichierXML):
    """
    Crue10 modele
    - id <str>: modele identifier
    - liste_sous_modeles <[SousModele]>: list of sous_modeles
    - noeuds_ic <dict>: initial condition at noeuds
    - casiers_ic <dict>: initial condition at casiers
    - branches_ic <dict>: initial condition at branches
    - graph <networkx.DiGraph>: directed graph with all nodes and active branches
    """

    FILES_XML = ['optr', 'optg', 'opti', 'pnum', 'dpti']
    FILES_XML_WITHOUT_TEMPLATE = ['optr', 'optg', 'opti', 'pnum']

    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, model_name, access='r', files=None, metadata=None):
        """
        :param model_name: modele name
        :param files: dict with xml path files
        :param metadata: dict containing metadata
        """
        check_preffix(model_name, 'Mo_')
        self.id = model_name
        super().__init__(access, files, metadata)

        self.liste_sous_modeles = []
        self._graph = None

        # Initial conditions
        self.noeuds_ic = OrderedDict()
        self.casiers_ic = OrderedDict()
        self.branches_ic = OrderedDict()

    @property
    def graph(self):
        if self._graph is None:
            self._build_graph()
        return self._graph

    @staticmethod
    def rename_emh(dictionary, old_id, new_id, replace_obj=True):
        dictionary[new_id] = dictionary.pop(old_id)
        if replace_obj:
            dictionary[new_id].id = new_id

    @staticmethod
    def rename_key_and_obj(dictionary, suffix, replace_obj=True, insert_before=False, emhs_to_preserve=[]):
        """Add suffix to all keys of dictionary and `id` attribute of objects"""
        for old_id in deepcopy(list(dictionary.keys())):
            if old_id not in emhs_to_preserve:
                if insert_before or old_id.endswith('_Am') or old_id.endswith('_Av'):
                    new_left_id, new_right_id = old_id.rsplit('_', 1)
                    new_id = new_left_id + suffix + '_' + new_right_id
                else:
                    new_id = old_id + suffix
                Modele.rename_emh(dictionary, old_id, new_id, replace_obj)

    def rename_noeud(self, old_id, new_id):
        logger.debug("Renommage Noeud: %s -> %s" % (old_id, new_id))
        for sous_modele in self.liste_sous_modeles:
            Modele.rename_emh(sous_modele.noeuds, old_id, new_id)
            Modele.rename_emh(self.noeuds_ic, old_id, new_id, replace_obj=False)

    def rename_emhs(self, suffix, emh_list=['Fk', 'Nd', 'Cd', 'St', 'Br'], emhs_to_preserve=[]):
        for sous_modele in self.liste_sous_modeles:
            if 'Fk' in emh_list:
                Modele.rename_key_and_obj(sous_modele.lois_frottement, suffix)
            if 'Nd' in emh_list:
                Modele.rename_key_and_obj(sous_modele.noeuds, suffix, emhs_to_preserve=emhs_to_preserve)
                Modele.rename_key_and_obj(self.noeuds_ic, suffix, emhs_to_preserve=emhs_to_preserve, replace_obj=False)
            if 'Cd' in emh_list:
                Modele.rename_key_and_obj(sous_modele.casiers, suffix)
                Modele.rename_key_and_obj(self.casiers_ic, suffix, replace_obj=False)
                Modele.rename_key_and_obj(sous_modele.profils_casier, suffix, insert_before=True)
            if 'St' in emh_list:
                Modele.rename_key_and_obj(sous_modele.sections, suffix)
                for st in sous_modele.get_liste_sections_profil():
                    st.set_profilsection_name()
            if 'Br' in emh_list:
                Modele.rename_key_and_obj(sous_modele.branches, suffix)
                Modele.rename_key_and_obj(self.branches_ic, suffix, replace_obj=False)

    def get_sous_modele(self, nom_sous_modele):
        for sous_modele in self.liste_sous_modeles:
            if sous_modele.id == nom_sous_modele:
                return sous_modele
        raise ExceptionCrue10("Le sous-modèle %s n'existe pas dans le modèle %s" % (nom_sous_modele, self.id))

    def get_noeud(self, nom_noeud):
        noeuds = []
        for noeud in self.get_liste_noeuds():
            if noeud.id == nom_noeud:
                noeuds.append(noeud)
        if len(noeuds) == 0:
            raise ExceptionCrue10("Le noeud %s n'est pas dans le %s" % (nom_noeud, self))
        elif len(noeuds) == 1:
            return noeuds[0]
        else:
            raise ExceptionCrue10("Le noeud %s existe dans plusieurs sous-modèles différents "
                                  "et ne peut pas être obtenu avec cette méthode" % nom_noeud)

    def get_section(self, nom_section):
        for section in self.get_liste_sections():
            if section.id == nom_section:
                return section
        raise ExceptionCrue10("La section %s n'est pas dans le %s" % (nom_section, self))

    def get_branche(self, nom_branche):
        for branche in self.get_liste_branches():
            if branche.id == nom_branche:
                return branche
        raise ExceptionCrue10("La branche %s n'est pas dans le %s" % (nom_branche, self))

    def get_casier(self, nom_casier):
        for casier in self.get_liste_casiers():
            if casier.id == nom_casier:
                return casier
        raise ExceptionCrue10("Le casier %s n'est pas dans le %s" % (nom_casier, self))

    def get_loi_frottement(self, nom_loi_frottement):
        for loi in self.get_liste_lois_frottement():
            if loi.id == nom_loi_frottement:
                return loi
        raise ExceptionCrue10("La loi de frottement %s n'est pas dans le %s" % (nom_loi_frottement, self))

    def get_liste_noeuds(self):
        noeuds = []
        for sous_modele in self.liste_sous_modeles:
            noeuds += sous_modele.get_liste_noeuds()
        return noeuds

    def get_liste_casiers(self):
        casiers = []
        for sous_modele in self.liste_sous_modeles:
            casiers += sous_modele.get_liste_casiers()
        return casiers

    def get_liste_sections(self, section_type=None, ignore_inactive=False):
        sections = []
        for sous_modele in self.liste_sous_modeles:
            sections += sous_modele.get_liste_sections(section_type=section_type,
                                                       ignore_inactive=ignore_inactive)
        return sections

    def get_liste_branches(self, filter_branch_types=None):
        branches = []
        for sous_modele in self.liste_sous_modeles:
            branches += sous_modele.get_liste_branches(filter_branch_types=filter_branch_types)
        return branches

    def get_liste_lois_frottement(self, ignore_sto=False):
        lois = []
        for sous_modele in self.liste_sous_modeles:
            lois += sous_modele.get_liste_lois_frottement(ignore_sto=ignore_sto)
        return lois

    def get_missing_active_sections(self, section_id_list):
        """
        Returns the list of the requested sections which are not found (or not active) in the current modele
            (section type is not checked)
        @param section_id_list: list of section identifiers
        """
        return set([st.id for st in self.get_liste_sections(ignore_inactive=True)]).difference(set(section_id_list))

    def get_duplicated_noeuds(self):
        return [nd for nd, count in Counter([noeud.id for noeud in self.get_liste_noeuds()]).items() if count > 1]

    def get_duplicated_casiers(self):
        return [ca for ca, count in Counter([casier.id for casier in self.get_liste_casiers()]).items() if count > 1]

    def get_duplicated_sections(self):
        return [st for st, count in Counter([section.id for section in self.get_liste_sections()]).items() if count > 1]

    def get_duplicated_branches(self):
        return [br for br, count in Counter([branche.id for branche in self.get_liste_branches()]).items() if count > 1]

    def get_theta_preissmann(self):
        return float(self.xml_trees['pnum'].find(PREFIX + 'ParamNumCalcTrans').find(PREFIX + 'ThetaPreissmann').text)

    def get_branche_barrage(self):
        liste_branches = []
        for branche in self.get_liste_branches():
            if isinstance(branche, BrancheBarrageFilEau) or isinstance(branche, BrancheBarrageGenerique):
                liste_branches.append(branche)
        if len(liste_branches) == 0:
            raise ExceptionCrue10("Aucune branche barrage (14 ou 15) dans le sous-modèle")
        if len(liste_branches) > 1:
            raise ExceptionCrue10("Plusieurs branches barrages (14 ou 15) dans le sous-modèle : %s" % liste_branches)
        return liste_branches[0]

    def _get_pnum_CalcPseudoPerm(self):
        return self.xml_trees['pnum'].find(PREFIX + 'ParamNumCalcPseudoPerm')

    def get_pnum_CalcPseudoPerm_NbrPdtDecoup(self):
        return int(self._get_pnum_CalcPseudoPerm().find(PREFIX + 'NbrPdtDecoup').text)

    def get_pnum_CalcPseudoPerm_NbrPdtMax(self):
        return int(self._get_pnum_CalcPseudoPerm().find(PREFIX + 'NbrPdtMax').text)

    def get_pnum_CalcPseudoPerm_TolMaxZ(self):
        return float(self._get_pnum_CalcPseudoPerm().find(PREFIX + 'TolMaxZ').text)

    def get_pnum_CalcPseudoPerm_TolMaxQ(self):
        return float(self._get_pnum_CalcPseudoPerm().find(PREFIX + 'TolMaxQ').text)

    def get_pnum_CalcPseudoPerm_PdtCst(self):
        pdt_elt = self._get_pnum_CalcPseudoPerm().find(PREFIX + 'Pdt')
        pdtcst_elt = pdt_elt.find(PREFIX + 'PdtCst')
        if pdtcst_elt is None:
            print(etree.tostring(pdt_elt))
            raise ExceptionCrue10("Le pas de temps n'est pas constant")
        return duration_iso8601_to_seconds(pdtcst_elt.text)

    def ajouter_sous_modele(self, sous_modele):
        check_isinstance(sous_modele, SousModele)
        if sous_modele.id in self.liste_sous_modeles:
            raise ExceptionCrue10("Le sous-modèle %s est déjà présent" % sous_modele.id)
        self.liste_sous_modeles.append(sous_modele)

    def ajouter_depuis_modele(self, modele):
        """Add modele in current modele with the related initial conditions"""
        for sous_modele in modele.liste_sous_modeles:
            self.ajouter_sous_modele(sous_modele)

        # Copy initial conditions
        for noeud_id, value in modele.noeuds_ic.items():
            self.noeuds_ic[noeud_id] = value
        for branche_id, values in modele.branches_ic.items():
            self.branches_ic[branche_id] = values
        for casier_id, value in modele.casiers_ic.items():
            self.casiers_ic[casier_id] = value

    def _build_graph(self):
        try:
            import networkx as nx
        except ImportError:  # ModuleNotFoundError not available in Python2
            raise ExceptionCrue10("Le module networkx ne fonctionne pas !")

        self._graph = nx.DiGraph()
        for noeud in self.get_liste_noeuds():
            self._graph.add_node(noeud.id)  # This step is necessary to import potential orphan nodes
        for branche in self.get_liste_branches():
            if branche.is_active:
                weight = 1 if branche.type in (1, 20) else 10  # branches in minor bed are favoured
                self._graph.add_edge(branche.noeud_amont.id, branche.noeud_aval.id,
                                     branche=branche.id, weight=weight)

    def get_branches_liste_entre_noeuds(self, noeud_amont_id, noeud_aval_id):
        try:
            import networkx as nx
        except ImportError:  # ModuleNotFoundError not available in Python2
            raise ExceptionCrue10("Le module networkx ne fonctionne pas !")

        try:
            path = nx.shortest_path(self.graph, noeud_amont_id, noeud_aval_id, weight='weight')  # minimize weight
        except nx.exception.NetworkXException as e:
            raise ExceptionCrue10("PROBLÈME AVEC LE GRAPHE : %s" % e)

        branches_list = []
        for u, v in zip(path, path[1:]):
            edge_data = self.graph.get_edge_data(u, v)
            nom_branche = edge_data['branche']
            branches_list.append(self.get_branche(nom_branche))
        return branches_list

    def set_pnum_CalcPseudoPerm_TolMaxZ(self, value):
        check_isinstance(value, float)
        self._get_pnum_CalcPseudoPerm().find(PREFIX + 'TolMaxZ').text = str(value)

    def set_pnum_CalcPseudoPerm_TolMaxQ(self, value):
        check_isinstance(value, float)
        self._get_pnum_CalcPseudoPerm().find(PREFIX + 'TolMaxQ').text = str(value)

    def set_pnum_CalcPseudoPerm_PdtCst(self, value):
        """
        Affecte le pas de temps constant demandé
        Attention si le pas de temps était variable, il est bien mis constant à la valeur demandée sans avertissement.
        """
        check_isinstance(value, float)
        pdt_elt = self._get_pnum_CalcPseudoPerm().find(PREFIX + 'Pdt')
        # Remove existing elements
        for elt in pdt_elt:
            pdt_elt.remove(elt)
        # Add new single element
        sub_elt = etree.SubElement(pdt_elt, PREFIX + 'PdtCst')
        sub_elt.text = duration_seconds_to_iso8601(value)

    def supprimer_noeuds_entre_deux_branches_fluviales(self):
        """
        Remove all intermediate removable nodes which are located between 2 adjacent fluvial branches
        Downstream Branche and the intermediate SectionIdem are safely removed
        Beware: boundary conditions are not checked yet!
        """
        for sous_modele in self.liste_sous_modeles:
            for noeud in sous_modele.get_liste_noeuds():
                if sous_modele.is_noeud_supprimable(noeud):
                    old_branche = sous_modele.supprimer_noeud_entre_deux_branches_fluviales(noeud)

                    # Remove obsolete initial conditions
                    self.noeuds_ic.pop(noeud.id)
                    self.branches_ic.pop(old_branche.id)

    def reset_initial_conditions(self):
        """Set initial conditions to default values"""
        self.noeuds_ic = OrderedDict([(noeud.id, 1.0E30) for noeud in self.get_liste_noeuds()])

        self.casiers_ic = OrderedDict([(casier.id, 0.0) for casier in self.get_liste_casiers()])

        self.branches_ic = OrderedDict()
        for branche in self.get_liste_branches():
            self.branches_ic[branche.id] = {
                'type': branche.type,
                'values': {'Qini': 0.0},
            }
            if branche.type == 5:
                self.branches_ic[branche.id]['values']['Ouv'] = 100.0
                self.branches_ic[branche.id]['values']['SensOuv'] = 'OuvVersHaut'
            elif branche.type == 20:
                self.branches_ic[branche.id]['values']['Qruis'] = 0.0

    def _read_dpti(self):
        """
        Read dpti.xml file
        """
        self.reset_initial_conditions()

        for emh_group in self._get_xml_root_and_set_comment('dpti'):

            if emh_group.tag == (PREFIX + 'DonPrtCIniNoeuds'):
                for emh_ci in emh_group.findall(PREFIX + 'DonPrtCIniNoeudNiveauContinu'):
                    self.noeuds_ic[emh_ci.get('NomRef')] = float(emh_ci.find(PREFIX + 'Zini').text)

            elif emh_group.tag == (PREFIX + 'DonPrtCIniCasiers'):
                for emh_ci in emh_group.findall(PREFIX + 'DonPrtCIniCasierProfil'):
                    self.casiers_ic[emh_ci.get('NomRef')] = float(emh_ci.find(PREFIX + 'Qruis').text)

            elif emh_group.tag == (PREFIX + 'DonPrtCIniBranches'):
                for emh_ci in emh_group:
                    branche_id = emh_ci.get('NomRef')
                    self.branches_ic[branche_id] = {
                        'type': 0,  # Arbitrary value which has to be different from 5 and 20
                        'values': {'Qini': float(emh_ci.find(PREFIX + 'Qini').text)},
                    }
                    if emh_ci.tag == PREFIX + 'DonPrtCIniBrancheOrifice':
                        self.branches_ic[branche_id]['type'] = 5
                        self.branches_ic[branche_id]['values']['Ouv'] = float(emh_ci.find(PREFIX + 'Ouv').text)
                        self.branches_ic[branche_id]['values']['SensOuv'] = emh_ci.find(PREFIX + 'SensOuv').text
                    elif emh_ci.tag == PREFIX + 'DonPrtCIniBrancheSaintVenant':
                        self.branches_ic[branche_id]['type'] = 20
                        self.branches_ic[branche_id]['values']['Qruis'] = float(emh_ci.find(PREFIX + 'Qruis').text)

    def read_all(self):
        if not self.was_read:
            self._set_xml_trees()

            for sous_modele in self.liste_sous_modeles:
                sous_modele.read_all()

            self._read_dpti()
        self.was_read = True

    def _write_dpti(self, folder):
        self._write_xml_file(
            'dpti', folder,
            noeuds_ci=self.noeuds_ic,
            casiers_ci=self.casiers_ic,
            branches_ci=self.branches_ic,
        )

    def write_all(self, folder, folder_config):
        logger.debug("Écriture du %s dans %s" % (self, folder))

        # Create folder if not existing
        if not os.path.exists(folder):
            os.makedirs(folder)

        for xml_type in Modele.FILES_XML_WITHOUT_TEMPLATE:
            xml_path = os.path.join(folder, os.path.basename(self.files[xml_type]))
            if self.xml_trees:
                write_xml_from_tree(self.xml_trees[xml_type], xml_path)
            else:
                write_default_xml_file(xml_type, xml_path)

        self._write_dpti(folder)

        for sous_modele in self.liste_sous_modeles:
            sous_modele.write_all(folder, folder_config)

    def write_topological_graph(self, out_files, nodesep=0.8, prog='dot'):
        try:
            import pydot
        except ImportError:  # ModuleNotFoundError not available in Python2
            raise ExceptionCrue10("Le module pydot ne fonctionne pas !")

        check_isinstance(out_files, list)
        # Create a directed graph
        graph = pydot.Dot(graph_type='digraph', label=self.id, fontsize=MO_FONTSIZE,
                          nodesep=nodesep, prog=prog)  # vertical : rankdir='LR'
        for sous_modele in self.liste_sous_modeles:
            subgraph = pydot.Cluster(sous_modele.id, label=sous_modele.id, fontsize=SM_FONTSIZE,
                                     style=key_from_constant(sous_modele.is_active, SM_STYLE))

            # Add nodes
            for _, noeud in sous_modele.noeuds.items():
                name = noeud.id
                connected_casier = sous_modele.get_connected_casier(noeud)
                has_casier = connected_casier is not None
                is_active = True
                if has_casier:
                    is_active = connected_casier.is_active
                    name += '\n(%s)' % connected_casier.id
                node = pydot.Node(noeud.id, label=name, fontsize=EMH_FONTSIZE, style="filled",
                                  fillcolor=key_from_constant(is_active, NODE_COLOR),
                                  shape=key_from_constant(has_casier, CASIER_SHAPE))
                subgraph.add_node(node)

            # Add branches
            for branche in sous_modele.get_liste_branches():
                direction = 'forward'
                if isinstance(branche, BrancheOrifice):
                    if branche.SensOrifice == 'Bidirect':
                        direction = 'both'
                    elif branche.SensOrifice == 'Indirect':
                        direction = 'back'
                edge = pydot.Edge(
                    branche.noeud_amont.id, branche.noeud_aval.id, label=branche.id, fontsize=EMH_FONTSIZE,
                    arrowhead=key_from_constant(branche.type, BRANCHE_ARROWHEAD),
                    arrowtail=key_from_constant(branche.type, BRANCHE_ARROWHEAD),
                    dir=direction,
                    style=key_from_constant(branche.is_active, BRANCHE_ARROWSTYLE),
                    color=key_from_constant(branche.type, BRANCHE_COLORS),
                    fontcolor=key_from_constant(branche.type, BRANCHE_COLORS),
                    penwidth=key_from_constant(branche.type, BRANCHE_SIZE),
                    # shape="dot"
                )
                subgraph.add_edge(edge)
            graph.add_subgraph(subgraph)

        # Export(s) to png, svg, dot...
        for out_file in out_files:
            if out_file:
                logger.debug("Génération du fichier %s (nodesep=%s, prog=%s)" % (out_file, nodesep, prog))
                if out_file.endswith('.png'):
                    graph.write_png(out_file)
                elif out_file.endswith('.svg'):
                    graph.write_svg(out_file)
                elif out_file.endswith('.dot'):
                    graph.write_dot(out_file)
                else:
                    raise ExceptionCrue10("Le format de fichier de `%s` n'est pas supporté" % out_file)

    def write_mascaret_geometry(self, geo_path):
        """
        @brief: Convert modele to Mascaret geometry format (extension: geo or georef)
        Only active branche of type 20 (SaintVenant) are written
        TODO: Add min/maj delimiter
        @param geo_path <str>: output file path
            Submodels branches should only contain SectionProfil
            (call to method `convert_sectionidem_to_sectionprofil` is highly recommanded)
        """
        geofile = MascaretGeoFile(geo_path, access='w')
        i_section = 0
        for sous_modele in self.liste_sous_modeles:
            for i_branche, branche in enumerate(sous_modele.get_liste_branches([20])):
                if branche.has_geom() and branche.is_active:
                    reach = Reach(i_branche, name=branche.id)
                    for section in branche.liste_sections_dans_branche:
                        if not isinstance(section, SectionProfil):
                            raise ExceptionCrue10("The `%s`, which is not a SectionProfil, could not be written" % section)
                        masc_section = Section(i_section, section.xp, name=section.id)
                        coord = np.array(section.get_coord(add_z=True))
                        masc_section.set_points_from_xyz(coord[:, 0], coord[:, 1], coord[:, 2])
                        pt_at_axis = section.interp_point(section.xt_axe)
                        masc_section.axis = (pt_at_axis.x, pt_at_axis.y)
                        reach.add_section(masc_section)
                        i_section += 1
                    geofile.add_reach(reach)
        geofile.save()

    def write_shp_sectionprofil_as_points(self, shp_path):
        schema = {'geometry': '3D Point', 'properties': {'id_section': 'str', 'Z': 'float'}}
        with fiona.open(shp_path, 'w', driver='ESRI Shapefile', schema=schema) as out_shp:
            for sous_modele in self.liste_sous_modeles:
                for section in sous_modele.get_liste_sections(SectionProfil, ignore_inactive=True):
                    coords = section.get_coord(add_z=True)
                    for coord in coords:
                        out_shp.write({'geometry': mapping(Point(coord)),
                                       'properties': {'id_section': section.id, 'Z': coord[-1]}})

    def write_shp_limites_lits_numerotes(self, shp_path):
        schema = {'geometry': 'LineString', 'properties': {'id_limite': 'str', 'id_branche': 'str'}}
        with fiona.open(shp_path, 'w', driver='ESRI Shapefile', schema=schema) as out_shp:
            for sous_modele in self.liste_sous_modeles:
                for branche in sous_modele.get_liste_branches():
                    for i_lit, lit_name in enumerate(LitNumerote.LIMIT_NAMES):
                        coords = []
                        for section in branche.liste_sections_dans_branche:
                            if isinstance(section, SectionProfil):
                                if i_lit == 0:
                                    point = section.interp_point(section.lits_numerotes[0].xt_min)
                                else:
                                    point = section.interp_point(section.lits_numerotes[i_lit - 1].xt_max)
                                coords.append((point.x, point.y))
                        if len(coords) > 2:
                            out_shp.write({'geometry': mapping(LineString(coords)),
                                           'properties': {'id_limite': lit_name, 'id_branche': branche.id}})

    def log_duplicated_emh(self):
        duplicated_noeuds = self.get_duplicated_noeuds()
        if duplicated_noeuds:
            logger.info("Noeuds dupliqués: %s" % duplicated_noeuds)

        duplicated_casiers = self.get_duplicated_casiers()
        if duplicated_casiers:
            logger.info("Casiers dupliqués: %s" % duplicated_casiers)

        duplicated_sections = self.get_duplicated_sections()
        if duplicated_sections:
            logger.warn("Sections dupliquées: %s" % duplicated_sections)

        duplicated_branches = self.get_duplicated_branches()
        if duplicated_branches:
            logger.warn("Branches dupliquées: %s" % duplicated_branches)

    def summary(self):
        return "%s: %i sous-modèle(s)" % (self, len(self.liste_sous_modeles))

    def __repr__(self):
        return "Modèle %s" % self.id
