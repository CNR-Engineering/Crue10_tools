# coding: utf-8
from builtins import super  # Python2 fix
from collections import Counter, OrderedDict
from copy import deepcopy
import fiona
from lxml import etree
import numpy as np
import os.path
from shapely.geometry import LineString, mapping, Point

from crue10.base import EnsembleFichiersXML
from crue10.emh.branche import BrancheOrifice, BrancheBarrageFilEau, BrancheBarrageGenerique
from crue10.emh.section import SectionProfil, LitNumerote
from crue10.utils import check_isinstance, check_preffix, DATA_FOLDER_ABSPATH, duration_iso8601_to_seconds, \
    duration_seconds_to_iso8601, get_xml_root_from_file, logger, PREFIX, write_default_xml_file, write_xml_from_tree
from crue10.utils.graph_1d_model import *
from crue10.sous_modele import SousModele


class Modele(EnsembleFichiersXML):
    """
    Modèle Crue10

    :param id: nom du modèle
    :vartype id: str
    :ivar liste_sous_modeles: liste des sous-modèles
    :vartype liste_sous_modeles: list(SousModele)
    :ivar noeuds_ic: conditions initiales aux noeuds (Zini)
    :vartype noeuds_ic: OrderedDict
    :ivar casiers_ic: conditions initiales aux casiers (Qruis)
    :vartype casiers_ic: OrderedDict
    :ivar branches_ic: conditions initiales aux branches (Qini et selon les types de branches : Qruis, Ouv et SensOuv)
    :vartype branches_ic: OrderedDict
    :ivar graph: graphe orienté avec tous les noeuds et branches actives
    :vartype graph: networkx.DiGraph
    """

    FILES_XML = ['optr', 'optg', 'opti', 'pnum', 'dpti', 'dreg']
    FILES_XML_WITHOUT_TEMPLATE = ['optr', 'optg', 'opti', 'pnum', 'dreg']

    METADATA_FIELDS = ['Type', 'IsActive', 'Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif',
                       'DateDerniereModif']

    def __init__(self, nom_modele, mode='r', files=None, metadata=None, version_grammaire=None):
        """
        :param nom_modele: nom du modèle
        :type nom_modele: str
        :param mode: accès en lecture ('r') ou écriture ('w')
        :type mode: str
        :param files: dictionnaire des chemins vers les fichiers xml
        :type files: dict(str)
        :param metadata: dictionnaire avec les méta-données
        :type metadata: dict(str)
        :param version_grammaire: version de la grammaire
        :type version_grammaire: str
        """
        check_preffix(nom_modele, 'Mo_')
        self.id = nom_modele
        super().__init__(mode, files, metadata, version_grammaire=version_grammaire)

        self.liste_sous_modeles = []
        self._graph = None

        # Initial conditions
        self.noeuds_ic = OrderedDict()
        self.casiers_ic = OrderedDict()
        self.branches_ic = OrderedDict()

    @property
    def graph(self):
        """Graphe orienté avec les noeuds et les branches du modèle"""
        if self._graph is None:
            self._build_graph()
        return self._graph

    @staticmethod
    def rename_emh(dictionary, old_id, new_id, replace_obj=True):
        """Renommer une EMH (changer son attribut id) dans un dictionnaire"""
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
        """Renommer un noeud"""
        logger.debug("Renommage Noeud: %s -> %s" % (old_id, new_id))
        for sous_modele in self.liste_sous_modeles:
            Modele.rename_emh(sous_modele.noeuds, old_id, new_id)
            Modele.rename_emh(self.noeuds_ic, old_id, new_id, replace_obj=False)

    def rename_emhs(self, suffix, emh_list=['Fk', 'Nd', 'Cd', 'St', 'Br'], emhs_to_preserve=[]):
        """
        Renommer les EMHs de tous les sous-modèles du modèle courant

        :param suffix: suffixe à ajouter aux EMHs
            (pour les sections sans géométrie, le suffixe à ajouter est mis avant le suffixe `_Am` ou `_Av`)
        :type suffix: str
        :param emh_list: liste des types d'EMHs à renommer
        :type emh_list: list(str)
        :param emhs_to_preserve: liste des noeuds à ne pas renommer
        :type emhs_to_preserve: list(str)
        """
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
        """
        :param nom_sous_modele: nom du sous-modèle
        :type nom_sous_modele: str
        :return: sous-modèle demandé
        :rtype: SousModele
        """
        for sous_modele in self.liste_sous_modeles:
            if sous_modele.id == nom_sous_modele:
                return sous_modele
        raise ExceptionCrue10("Le sous-modèle %s n'existe pas dans le modèle %s" % (nom_sous_modele, self.id))

    def get_noeud(self, nom_noeud):
        """
        :param nom_noeud: nom du noeud
        :type nom_noeud: str
        :return: noeud demandé
        :rtype: Noeud
        """
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
        """
        :param nom_section: nom de la section
        :type nom_section: str
        :return: section demandée
        :rtype: Section
        """
        for section in self.get_liste_sections():
            if section.id == nom_section:
                return section
        raise ExceptionCrue10("La section %s n'est pas dans le %s" % (nom_section, self))

    def get_branche(self, nom_branche):
        """
        :param nom_branche: nom de la branche
        :type nom_branche: str
        :return: branche demandée
        :rtype: Branche
        """
        for branche in self.get_liste_branches():
            if branche.id == nom_branche:
                return branche
        raise ExceptionCrue10("La branche %s n'est pas dans le %s" % (nom_branche, self))

    def get_casier(self, nom_casier):
        """
        :param nom_casier: nom du casier
        :type nom_casier: str
        :return: casier demandé
        :rtype: Casier
        """
        for casier in self.get_liste_casiers():
            if casier.id == nom_casier:
                return casier
        raise ExceptionCrue10("Le casier %s n'est pas dans le %s" % (nom_casier, self))

    def get_loi_frottement(self, nom_loi_frottement):
        """
        :param nom_loi_frottement: nom de la loi de frottement
        :type nom_loi_frottement: str
        :return: loi de frottement demandée
        :rtype: LoiFrottement
        """
        for loi in self.get_liste_lois_frottement():
            if loi.id == nom_loi_frottement:
                return loi
        raise ExceptionCrue10("La loi de frottement %s n'est pas dans le %s" % (nom_loi_frottement, self))

    def get_liste_noeuds(self):
        """
        :return: liste des noeuds
        :rtype: list(Noeud)
        """
        noeuds = []
        for sous_modele in self.liste_sous_modeles:
            noeuds += sous_modele.get_liste_noeuds()
        return noeuds

    def get_liste_casiers(self):
        """
        :return: liste des casiers
        :rtype: list(Casier)
        """
        casiers = []
        for sous_modele in self.liste_sous_modeles:
            casiers += sous_modele.get_liste_casiers()
        return casiers

    def get_liste_sections(self, section_type=None, ignore_inactive=False):
        """
        :param section_type: classe du type de section (ie. classe fille de `Section`, par ex. `SectionProfil`)
        :type section_type: class, optional
        :param ignore_inactive:
        :type ignore_inactive: bool, optional
        :return: liste des sections
        :rtype: list(Section)
        """
        sections = []
        for sous_modele in self.liste_sous_modeles:
            sections += sous_modele.get_liste_sections(section_type=section_type,
                                                       ignore_inactive=ignore_inactive)
        return sections

    def get_liste_branches(self, filter_branch_types=None):
        """
        :param filter_branch_types: liste des types de branches
        :type filter_branch_types: [int]
        :return: liste des branches
        :rtype: list(Branche)
        """
        branches = []
        for sous_modele in self.liste_sous_modeles:
            branches += sous_modele.get_liste_branches(filter_branch_types=filter_branch_types)
        return branches

    def get_liste_lois_frottement(self, ignore_sto=False):
        """
        :param ignore_sto: True pour ignorer les lois de type `FkSto`
        :type ignore_sto: bool, optional
        :return: liste des lois de frottement
        :rtype: list(LoiFrottement)
        """
        lois = []
        for sous_modele in self.liste_sous_modeles:
            lois += sous_modele.get_liste_lois_frottement(ignore_sto=ignore_sto)
        return lois

    def get_missing_active_sections(self, section_id_list):
        """
        Returns the list of the requested sections which are not found (or not active) in the current modele
        (section type is not checked)

        :param section_id_list: list of section identifiers
        """
        return set([st.id for st in self.get_liste_sections(ignore_inactive=True)]).difference(set(section_id_list))

    def get_duplicated_noeuds(self):
        """
        :return: liste des noeuds dupliqués
        :rtype: list(Noeud)
        """
        return [nd for nd, count in Counter([noeud.id for noeud in self.get_liste_noeuds()]).items() if count > 1]

    def get_duplicated_casiers(self):
        """
        :return: liste des casiers dupliqués
        :rtype: list(Casier)
        """
        return [ca for ca, count in Counter([casier.id for casier in self.get_liste_casiers()]).items() if count > 1]

    def get_duplicated_sections(self):
        """
        :return: liste des sections dupliquées
        :rtype: list(Section)
        """
        return [st for st, count in Counter([section.id for section in self.get_liste_sections()]).items() if count > 1]

    def get_duplicated_branches(self):
        """
        :return: liste des branches dupliquées
        :rtype: list(Branche)
        """
        return [br for br, count in Counter([branche.id for branche in self.get_liste_branches()]).items() if count > 1]

    def get_theta_preissmann(self):
        """
        :return: coefficient d'implicitation "Théta Preissmann"
        :rtype: float
        """
        return float(self.xml_trees['pnum'].find(PREFIX + 'ParamNumCalcTrans').find(PREFIX + 'ThetaPreissmann').text)

    def get_branche_barrage(self):
        """
        :return: branche barrage du modèle (active ou non)
        :rtype: BrancheBarrageFilEau | BrancheBarrageGenerique
        """
        liste_branches = []
        for branche in self.get_liste_branches():
            if isinstance(branche, BrancheBarrageFilEau) or isinstance(branche, BrancheBarrageGenerique):
                liste_branches.append(branche)
        if len(liste_branches) == 0:
            raise ExceptionCrue10("Aucune branche barrage (14 ou 15) dans le modèle")
        if len(liste_branches) > 1:
            raise ExceptionCrue10("Plusieurs branches barrages (14 ou 15) dans le modèle : %s" % liste_branches)
        return liste_branches[0]

    def _get_pnum_CalcPseudoPerm(self):
        return self.xml_trees['pnum'].find(PREFIX + 'ParamNumCalcPseudoPerm')

    def _get_pnum_CalcTrans(self):
        return self.xml_trees['pnum'].find(PREFIX + 'ParamNumCalcTrans')

    def get_pnum_CalcPseudoPerm_NbrPdtDecoup(self):
        """
        :return: NbrPdtDecoup des calculs pseudo-permanents
        :rtype: int
        """
        return int(self._get_pnum_CalcPseudoPerm().find(PREFIX + 'NbrPdtDecoup').text)

    def get_pnum_CalcPseudoPerm_NbrPdtMax(self):
        """
        :return: NbrPdtMax des calculs pseudo-permanents
        :rtype: int
        """
        return int(self._get_pnum_CalcPseudoPerm().find(PREFIX + 'NbrPdtMax').text)

    def get_pnum_CalcPseudoPerm_TolMaxZ(self):
        """
        :return: TolMaxZ des calculs pseudo-permanents
        :rtype: float
        """
        return float(self._get_pnum_CalcPseudoPerm().find(PREFIX + 'TolMaxZ').text)

    def get_pnum_CalcPseudoPerm_TolMaxQ(self):
        """
        :return: TolMaxQ des calculs pseudo-permanents
        :rtype: float
        """
        return float(self._get_pnum_CalcPseudoPerm().find(PREFIX + 'TolMaxQ').text)

    def get_pnum_CalcPseudoPerm_PdtCst(self):
        """
        :return: pas de temps constant des calculs pseudo-permanents
        :rtype: float
        """
        pdt_elt = self._get_pnum_CalcPseudoPerm().find(PREFIX + 'Pdt')
        pdtcst_elt = pdt_elt.find(PREFIX + 'PdtCst')
        if pdtcst_elt is None:
            logger.debug(etree.tostring(pdt_elt))
            raise ExceptionCrue10("Le pas de temps n'est pas constant")
        return duration_iso8601_to_seconds(pdtcst_elt.text)

    def get_pnum_CalcTrans_PdtCst(self):
        """
        :return: pas de temps constant des calculs transitoires
        :rtype: float
        """
        pdt_elt = self._get_pnum_CalcTrans().find(PREFIX + 'Pdt')
        pdtcst_elt = pdt_elt.find(PREFIX + 'PdtCst')
        if pdtcst_elt is None:
            logger.debug(etree.tostring(pdt_elt))
            raise ExceptionCrue10("Le pas de temps n'est pas constant")
        return duration_iso8601_to_seconds(pdtcst_elt.text)

    def ajouter_sous_modele(self, sous_modele):
        """
        Ajouter un sous-modèle au modèle

        :param sous_modele: sous-modèle à ajouter
        :type: SousModele
        """
        check_isinstance(sous_modele, SousModele)
        if sous_modele.id in self.liste_sous_modeles:
            raise ExceptionCrue10("Le sous-modèle %s est déjà présent" % sous_modele.id)
        self.liste_sous_modeles.append(sous_modele)

    def ajouter_depuis_modele(self, modele):
        """
        Ajouter tous les sous-modèles d'un modèle source avec ses conditions initiales au modèle courant

        :param sous_modele: modèle à ajouter
        :type: Modele
        """
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

    def get_liste_branches_entre_deux_noeuds(self, nom_noeud_amont, nom_noeud_aval):
        """
        Obtenir la liste des branches entre 2 noeuds
        (le chemin le plus court, en passant par des branches Saint-Venant est retenu)

        :param nom_noeud_amont: nom du noeud amont
        :type nom_noeud_amont: str
        :param nom_noeud_aval: nom du noeud aval
        :type nom_noeud_aval: str
        :rtype: list(Branche)
        """
        try:
            import networkx as nx
        except ImportError:  # ModuleNotFoundError not available in Python2
            raise ExceptionCrue10("Le module networkx ne fonctionne pas !")

        # Try if nodes exsit
        self.get_noeud(nom_noeud_amont)
        self.get_noeud(nom_noeud_aval)

        try:
            path = nx.shortest_path(self.graph, nom_noeud_amont, nom_noeud_aval, weight='weight')  # minimize weight
        except nx.exception.NetworkXException as e:
            raise ExceptionCrue10("PROBLÈME AVEC LE GRAPHE :\n%s" % e)

        branches = []
        for u, v in zip(path, path[1:]):
            edge_data = self.graph.get_edge_data(u, v)
            nom_branche = edge_data['branche']
            branches.append(self.get_branche(nom_branche))
        return branches

    def set_pnum_CalcPseudoPerm_TolMaxZ(self, value):
        """
        Affecter la tolérance TolMaxZ demandée pour les calculs pseudo-permanents

        :param value: valeur TolMaxZ à affecter
        :type value: float
        """
        check_isinstance(value, float)
        self._get_pnum_CalcPseudoPerm().find(PREFIX + 'TolMaxZ').text = str(value)

    def set_pnum_CalcPseudoPerm_TolMaxQ(self, value):
        """
        Affecter la tolérance TolMaxQ demandée pour les calculs pseudo-permanents

        :param value: valeur TolMaxQ à affecter
        :type value: float
        """
        check_isinstance(value, float)
        self._get_pnum_CalcPseudoPerm().find(PREFIX + 'TolMaxQ').text = str(value)

    def set_pnum_CalcPseudoPerm_PdtCst(self, value):
        """
        Affecter le pas de temps constant demandé pour les calculs pseudo-permanents
        Attention si le pas de temps était variable, il est bien mis constant à la valeur demandée sans avertissement.

        :param value: pas de temps à affecter
        :type value: float
        """
        check_isinstance(value, float)
        pdt_elt = self._get_pnum_CalcPseudoPerm().find(PREFIX + 'Pdt')
        # Remove existing elements
        for elt in pdt_elt:
            pdt_elt.remove(elt)
        # Add new single element
        sub_elt = etree.SubElement(pdt_elt, PREFIX + 'PdtCst')
        sub_elt.text = duration_seconds_to_iso8601(value)

    def set_pnum_CalcTrans_PdtCst(self, value):
        """
        Affecter le pas de temps constant demandé pour les calculs transitoires
        Attention si le pas de temps était variable, il est bien mis constant à la valeur demandée sans avertissement.

        :param value: pas de temps à affecter
        :type value: float
        """
        check_isinstance(value, float)
        pdt_elt = self._get_pnum_CalcTrans().find(PREFIX + 'Pdt')
        # Remove existing elements
        for elt in pdt_elt:
            pdt_elt.remove(elt)
        # Add new single element
        sub_elt = etree.SubElement(pdt_elt, PREFIX + 'PdtCst')
        sub_elt.text = duration_seconds_to_iso8601(value)

    def renommer(self, nom_modele_cible, folder):
        """
        Renommer le modèle courant

        :param nom_modele_cible: nouveau nom du modèle
        :type nom_modele_cible: str
        :param folder: dossier pour les fichiers XML
        :type folder: str
        """
        self.id = nom_modele_cible
        for xml_type in Modele.FILES_XML:
            self.files[xml_type] = os.path.join(folder, nom_modele_cible[3:] + '.' + xml_type + '.xml')

    def supprimer_noeuds_entre_branches_fluviales(self):
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

    def decouper_branche_fluviale(self, nom_sous_modele, nom_branche, nom_branche_nouvelle, nom_section, nom_noeud):
        """
        Découper une branche fluviale au niveau de la section cible intermédiaire (doit exister sur la branche),
        tout en conservant les conditions aux limites (interpolation linéaire du débit et de la cote au nouveau noeud)

        :param nom_sous_modele: nom du sous-modèle
        :type nom_sous_modele: str
        :param nom_branche: nom de la branche à découper
        :type nom_branche: str
        :param nom_branche_nouvelle: nom de la nouvelle branche (partie aval)
        :type nom_branche_nouvelle: str
        :param nom_section: nom de la section servant à la découpe
        :type nom_section: str
        :param nom_noeud: nom du noeud à créer
        :type nom_noeud: str
        """
        sous_modele = self.get_sous_modele(nom_sous_modele)
        branche = self.get_branche(nom_branche)

        nom_noeud_aval = branche.noeud_aval.id
        niveau_amont = self.noeuds_ic[branche.noeud_amont.id]
        niveau_aval = self.noeuds_ic[branche.noeud_aval.id]
        section_pos_ratio = sous_modele.decouper_branche_fluviale(nom_branche, nom_branche_nouvelle,
                                                                  nom_section, nom_noeud)
        self.branches_ic[nom_branche_nouvelle] = self.branches_ic[nom_branche]
        self.noeuds_ic[nom_noeud] = (1 - section_pos_ratio) * niveau_amont + section_pos_ratio * niveau_aval
        self.noeuds_ic[nom_noeud_aval] = niveau_aval

    def reset_initial_conditions(self):
        """
        Réinitialiser les conditions initiales aux valeurs par défaut
        """
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

        for emh_group in self._get_xml_root_set_version_grammaire_and_comment('dpti'):

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

    def read_all(self, ignore_shp=False):
        """
        Lire tous les fichiers du modèle
        """
        if not self.was_read:
            for sous_modele in self.liste_sous_modeles:
                sous_modele.read_all(ignore_shp=ignore_shp)

            self._read_dpti()
            self._set_xml_trees()  # should be after read_dpi to set version_grmamaire and check if dreg is expected
        self.was_read = True

    def _write_dpti(self, folder):
        """
        Écrire le fichier dpti.xml

        :param folder: dossier de sortie
        """
        self._write_xml_file(
            'dpti', folder,
            noeuds_ci=self.noeuds_ic,
            casiers_ci=self.casiers_ic,
            branches_ci=self.branches_ic,
        )

    def write_all(self, folder, folder_config):
        """
        Écrire tous les fichiers du modèle
        """

        logger.debug("Écriture du %s dans %s (grammaire %s)" % (self, folder, self.version_grammaire))

        # Create folder if not existing
        if not os.path.exists(folder):
            os.makedirs(folder)

        files_xml = deepcopy(Modele.FILES_XML_WITHOUT_TEMPLATE)
        if self.version_grammaire == '1.2':  # HARDCODED to support g1.2
            files_xml.remove('dreg')
        for xml_type in files_xml:
            try:
                xml_path = os.path.join(folder, os.path.basename(self.files[xml_type]))
                if self.xml_trees:
                    write_xml_from_tree(self.xml_trees[xml_type], xml_path)
                else:
                    write_default_xml_file(xml_type, self.version_grammaire, xml_path)
            except KeyError:
                raise ExceptionCrue10("Le fichier %s est absent !" % xml_type)

        self._write_dpti(folder)

        for sous_modele in self.liste_sous_modeles:
            sous_modele.write_all(folder, folder_config)

    def changer_version_grammaire(self, version_grammaire, shallow=False):
        """
        Changer la version de la grammaire

        :param version_grammaire: version de la grammaire cible
        :type version_grammaire: str
        :param shallow: conversion profonde si False, peu profonde sinon
        :type shallow: bool
        """
        if version_grammaire == '1.3':  # HARDCODED to support g1.2
            if 'dreg' not in self.xml_trees:
                # Add dreg in self.xml_trees if missing (because is from grammar v1.2)
                xml_path = os.path.join(DATA_FOLDER_ABSPATH, version_grammaire, 'fichiers_vierges', 'default.dreg.xml')
                root = get_xml_root_from_file(xml_path)
                self.xml_trees['dreg'] = root
                self.files['dreg'] = self.files['optr'][:-9] + '.dreg.xml'

        if not shallow:
            for sous_modele in self.liste_sous_modeles:
                sous_modele.changer_version_grammaire(version_grammaire)

        super().changer_version_grammaire(version_grammaire)

    def write_topological_graph(self, out_files, nodesep=0.8, prog='dot'):
        """
        Écrire un ensemble de fichiers (png, svg et/ou dot) représentant le schéma topologique du modèle

        :param out_files: liste des fichiers de sortie (l'extension détermine le format)
        :type out_files: list(str)
        :param nodesep: ratio pour modifier l'espacement (par ex. 0.5 ou 2)
        :type nodesep: float
        :param prog: outil de rendu
        :type prog: str
        """
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
        Convert modele to Mascaret geometry format (extension: geo or georef)
        Only active branche of type 20 (SaintVenant) are written
        TODO: Add min/maj delimiter
        :param geo_path <str>: output file path

        Submodels branches should only contain SectionProfil
        (call to method `convert_sectionidem_to_sectionprofil` is highly recommanded)
        """
        from mascaret.mascaret_file import Reach, Section
        from mascaret.mascaretgeo_file import MascaretGeoFile

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
        """
        Écrire un fichier SHP (de type point) avec les coordonnées x, y, z des SectionProfils

        :param shp_path: chemin vers le fichier SHP de sortie
        :type shp_path: str
        """
        schema = {'geometry': '3D Point', 'properties': {'id_section': 'str', 'Z': 'float'}}
        with fiona.open(shp_path, 'w', driver='ESRI Shapefile', schema=schema) as out_shp:
            for sous_modele in self.liste_sous_modeles:
                for section in sous_modele.get_liste_sections(SectionProfil, ignore_inactive=True):
                    coords = section.get_coord(add_z=True)
                    for coord in coords:
                        out_shp.write({'geometry': mapping(Point(coord)),
                                       'properties': {'id_section': section.id, 'Z': coord[-1]}})

    def write_shp_limites_lits_numerotes(self, shp_path):
        """
        Écrire un fichier SHP (de type polyligne ouverte) avec la délimitation des lits numérotés (pour chaque branche)

        :param shp_path: chemin vers le fichier SHP de sortie
        :type shp_path: str
        """
        schema = {'geometry': 'LineString', 'properties': {'id_limite': 'str', 'id_branche': 'str'}}
        with fiona.open(shp_path, 'w', driver='ESRI Shapefile', schema=schema) as out_shp:
            for sous_modele in self.liste_sous_modeles:
                for branche in sous_modele.get_liste_branches():
                    for i_limite, nom_limite in enumerate(LitNumerote.LIMIT_NAMES):
                        coords = []
                        for section in branche.liste_sections_dans_branche:
                            if isinstance(section, SectionProfil):
                                point = section.interp_point(section.get_xt_limite_lit(nom_limite))
                                coords.append((point.x, point.y))
                        if len(coords) > 2:
                            out_shp.write({'geometry': mapping(LineString(coords)),
                                           'properties': {'id_limite': nom_limite, 'id_branche': branche.id}})

    def log_duplicated_emh(self):
        """Logger les EMH dupliqués"""
        duplicated_noeuds = self.get_duplicated_noeuds()
        if duplicated_noeuds:
            logger.info("Noeuds dupliqués: %s" % duplicated_noeuds)

        duplicated_casiers = self.get_duplicated_casiers()
        if duplicated_casiers:
            logger.info("Casiers dupliqués: %s" % duplicated_casiers)

        duplicated_sections = self.get_duplicated_sections()
        if duplicated_sections:
            logger.warning("Sections dupliquées: %s" % duplicated_sections)

        duplicated_branches = self.get_duplicated_branches()
        if duplicated_branches:
            logger.warning("Branches dupliquées: %s" % duplicated_branches)

    def summary(self):
        return "%s: %i sous-modèle(s)" % (self, len(self.liste_sous_modeles))

    def __repr__(self):
        return "Modèle %s" % self.id
