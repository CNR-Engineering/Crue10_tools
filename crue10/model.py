# coding: utf-8
import os.path
import shutil

from crue10.utils import add_default_missing_metadata, check_isinstance, check_preffix, CrueError, logger, \
    XML_DEFAULT_FOLDER, XML_TEMPLATES_FOLDER
from crue10.utils.graph_1d_model import *

from .submodel import SubModel

try:
    import pydot
except:
    raise CrueError("Le module pydot ne fonctionne pas !")


class Model:
    """
    Crue10 model
    - id <str>: model identifier
    - files <{str}>: dict with path to xml files (keys correspond to `FILES_XML` list)
    - metadata <{dict}>: containing metadata (keys correspond to `METADATA_FIELDS` list)
    - comment <str>: information describing current model
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
        self.comment = comment
        self.was_read = False

        self.submodels = []
        # self.initial_conditions = {}
        # self.data = {}

        if 'Type' not in self.metadata:
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

    def get_section_list(self, ignore_inactive=False):
        sections = []
        for submodel in self.submodels:
            sections += submodel.iter_on_sections(ignore_inactive=ignore_inactive)
        return sections

    def get_missing_active_sections(self, section_id_list):
        """
        Returns the list of the requested sections which are not found (or not active) in the current model
            (section type is not checked)
        :param section_id_list: list of section identifiers
        """
        return set([st.id for st in self.get_section_list(ignore_inactive=True)]).difference(set(section_id_list))

    def add_submodel(self, submodel):
        check_isinstance(submodel, SubModel)
        if submodel.id in self.submodels:
            raise CrueError("Le sous-modèle %s est déjà présent" % submodel.id)
        self.submodels.append(submodel)

    def _read_dpti(self):
        """
        Read dpti.xml file
        """
        pass  # TODO

    def read_all(self):
        if not self.was_read:
            # TODO: Reading of ['optr', 'optg', 'opti', 'pnum', 'dpti'] is not supported yet!

            for submodel in self.submodels:
                submodel.read_all()

            self._read_dpti()
        self.was_read = True

    @staticmethod
    def _write_default_file(xml_type, file_path):
        shutil.copyfile(os.path.join(XML_DEFAULT_FOLDER, xml_type + '.xml'), file_path)

    def write_all(self, folder, folder_config):
        logger.debug("Writing %s in %s" % (self, folder))

        for xml_type in Model.FILES_XML:
            Model._write_default_file(xml_type, os.path.join(folder, os.path.basename(self.files[xml_type])))

        for submodel in self.submodels:
            submodel.write_all(folder, folder_config)

    def write_topological_graph(self, out_files, nodesep=0.8, prog='dot'):
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
                connected_casier = submodel.get_connected_casier(noeud.id)
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
                edge = pydot.Edge(
                    branche.noeud_amont.id, branche.noeud_aval.id, label=branche.id, fontsize=EMH_FONTSIZE,
                    arrowhead=key_from_constant(branche.type, BRANCHE_ARROWHEAD),
                    arrowtail=key_from_constant(branche.type, BRANCHE_ARROWHEAD),
                    # arrowtail="inv",
                    dir="forward",  # "both" or "back"
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
                    raise NotImplementedError

    def summary(self):
        return "%s: %i sous-modèle(s)" % (self, len(self.submodels))

    def __repr__(self):
        return "Modèle %s" % self.id
