# coding: utf-8
from collections import Counter
import os.path
import shutil
import xml.etree.ElementTree as ET

from crue10.emh.branche import BrancheOrifice
from crue10.utils import add_default_missing_metadata, check_isinstance, check_preffix, CrueError, JINJA_ENV, logger, \
    PREFIX, XML_DEFAULT_FOLDER, XML_ENCODING
from crue10.utils.graph_1d_model import *

from crue10.submodel import SubModel


class Model:
    """
    Crue10 model
    - id <str>: model identifier
    - files <{str}>: dict with path to xml files (keys correspond to `FILES_XML` list)
    - metadata <{dict}>: containing metadata (keys correspond to `METADATA_FIELDS` list)
    - submodels <[SubModel]>: list of submodels
    """

    FILES_XML = ['optr', 'optg', 'opti', 'pnum', 'dpti']
    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, model_name, access='r', files=None, metadata=None, comment=''):
        """
        :param model_name: model name
        :param files: dict with xml path files
        :param metadata: dict containing metadata
        """
        check_preffix(model_name, 'Mo_')
        self.id = model_name
        self.metadata = {} if metadata is None else metadata
        self.was_read = False

        self.submodels = []

        # Initial conditions
        self.noeuds_ic = {}
        self.casiers_ic = {}
        self.branches_ic = {}

        self.metadata['Type'] = 'Crue10'
        self.metadata = add_default_missing_metadata(self.metadata, Model.METADATA_FIELDS)

        if access == 'r':
            if files is None:
                raise RuntimeError
            if set(files.keys()) != set(Model.FILES_XML):
                raise RuntimeError
            self.files = files
        elif access == 'w':
            self.files = {}
            if files is None:
                for xml_type in Model.FILES_XML:
                    self.files[xml_type] = model_name[3:] + '.' + xml_type + '.xml'
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

    def get_noeud_list(self):
        noeuds = []
        for submodel in self.submodels:
            noeuds += [noeud for _, noeud in submodel.noeuds.items()]
        return noeuds

    def get_casier_list(self):
        casiers = []
        for submodel in self.submodels:
            casiers += [casier for _, casier in submodel.casiers.items()]
        return casiers

    def get_section_list(self, ignore_inactive=False):
        sections = []
        for submodel in self.submodels:
            sections += submodel.iter_on_sections(ignore_inactive=ignore_inactive)
        return sections

    def get_branche_list(self):
        branches = []
        for submodel in self.submodels:
            branches += submodel.iter_on_branches()
        return branches

    def get_missing_active_sections(self, section_id_list):
        """
        Returns the list of the requested sections which are not found (or not active) in the current model
            (section type is not checked)
        :param section_id_list: list of section identifiers
        """
        return set([st.id for st in self.get_section_list(ignore_inactive=True)]).difference(set(section_id_list))

    def get_duplicated_noeuds(self):
        return [nd for nd, count in Counter([noeud.id for noeud in self.get_noeud_list()]).items() if count > 1]

    def get_duplicated_casiers(self):
        return [ca for ca, count in Counter([casier.id for casier in self.get_casier_list()]).items() if count > 1]

    def get_duplicated_sections(self):
        return [st for st, count in Counter([section.id for section in self.get_section_list()]).items() if count > 1]

    def get_duplicated_branches(self):
        return [br for br, count in Counter([branche.id for branche in self.get_branche_list()]).items() if count > 1]

    def add_submodel(self, submodel):
        check_isinstance(submodel, SubModel)
        if submodel.id in self.submodels:
            raise CrueError("Le sous-modèle %s est déjà présent" % submodel.id)
        self.submodels.append(submodel)

    def reset_initial_conditions(self):
        self.noeuds_ic = {noeud.id: 1.0E30 for noeud in self.get_noeud_list()}

        self.casiers_ic = {casier.id: 0.0 for casier in self.get_casier_list()}

        self.branches_ic = {}
        for branche in self.get_branche_list():
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

        for emh_group in ET.parse(self.files['dpti']).getroot():

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
            # TODO: Reading of ['optr', 'optg', 'opti', 'pnum'] is not supported yet!

            for submodel in self.submodels:
                submodel.read_all()

            self._read_dpti()
        self.was_read = True

    def _write_dpti(self, folder):
        xml = 'dpti'
        template_render = JINJA_ENV.get_template(xml + '.xml').render(
            comment=self.comment,
            noeuds_ci=self.noeuds_ic,
            casiers_ci=self.casiers_ic,
            branches_ci=self.branches_ic,
        )
        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

    @staticmethod
    def _write_default_file(xml_type, file_path):
        shutil.copyfile(os.path.join(XML_DEFAULT_FOLDER, xml_type + '.xml'), file_path)

    def write_all(self, folder, folder_config):
        logger.debug("Writing %s in %s" % (self, folder))

        for xml_type in ['optr', 'optg', 'opti', 'pnum']:
            Model._write_default_file(xml_type, os.path.join(folder, os.path.basename(self.files[xml_type])))
        self._write_dpti(folder)

        for submodel in self.submodels:
            submodel.write_all(folder, folder_config)

    def write_topological_graph(self, out_files, nodesep=0.8, prog='dot'):
        try:
            import pydot
        except:
            raise CrueError("Le module pydot ne fonctionne pas !")

        check_isinstance(out_files, list)
        # Create a directed graph
        graph = pydot.Dot(graph_type='digraph', label=self.id, fontsize=MO_FONTSIZE,
                          nodesep=nodesep, prog=prog)  # vertical : rankdir='LR'
        for submodel in self.submodels:
            subgraph = pydot.Cluster(submodel.id, label=submodel.id, fontsize=SM_FONTSIZE,
                                     style=key_from_constant(submodel.is_active, SM_STYLE))

            # Add nodes
            for _, noeud in submodel.noeuds.items():
                name = noeud.id
                connected_casier = submodel.get_connected_casier(noeud)
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
            for branche in submodel.iter_on_branches():
                direction = 'forward'
                if isinstance(branche, BrancheOrifice):
                    if branche.SensOrifice == 'Bidirect':
                        direction= 'both'
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
                    raise CrueError("Le format de fichier de `%s` n'est pas supporté" % out_file)

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
        return "%s: %i sous-modèle(s)" % (self, len(self.submodels))

    def __repr__(self):
        return "Modèle %s" % self.id
