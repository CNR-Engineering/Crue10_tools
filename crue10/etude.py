# coding: utf-8
from builtins import super  # Python2 fix
from collections import OrderedDict
from copy import deepcopy
from io import open  # Python2 fix
import os.path
from shutil import rmtree
import time
import xml.etree.ElementTree as ET

from crue10.base import FichierXML
from crue10.modele import Modele
from crue10.run import Run
from crue10.scenario import Scenario
from crue10.sous_modele import SousModele
from crue10.utils import check_isinstance, ExceptionCrue10, JINJA_ENV, logger, PREFIX
from crue10.utils.settings import XML_ENCODING


def read_metadata(elt, keys):
    metadata = {}
    for field in keys:
        text = elt.find(PREFIX + field).text
        metadata[field] = '' if text is None else text
    return metadata


class Etude(FichierXML):
    """Étude Crue10

    :param access: 'r' to read and 'w' to write
    :type access: str
    :param folders: dict with folders (keys correspond to `FOLDERS` list)
    :type folders: {str}
    :param filename_list: list of xml file names
    :type filename_list: [str]
    :param nom_scenario_courant: current scenario identifier
    :type nom_scenario_courant: str
    :param scenarios: dict with scneario name and Scenario object
    :type scenarios: {str: Scenario}
    :param modeles: Dict with modele name and Modele object
    :type modeles: {str: Modele}
    :param liste_sous_modeles: Dictionnaire des sous-modèles (id: objet)
    :type liste_sous_modeles: {str: SousModele}
    """

    FOLDERS = OrderedDict([('CONFIG', 'Config'), ('FICHETUDES', '.'),
                           ('RAPPORTS', 'Rapports'), ('RUNS', 'Runs')])
    FILES_XML = ['etu']
    SUB_FILES_XML = Scenario.FILES_XML + Modele.FILES_XML + SousModele.FILES_XML
    METADATA_FIELDS = ['Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif', 'DateDerniereModif']

    def __init__(self, etu_path, folders=None, access='r', metadata=None, comment=''):
        """
        :param etu_path: Fichier étude Crue10 (*.etu.xml)
        :type etu_path: str
        :param folders: dictionnaire avec les sous-dossiers
        :type folders: OrderedDict(str)
        :param access: accès en lecture ('r') ou écriture ('w')
        :type access: str
        :param files: dictionnaire des chemins vers les fichiers xml
        :type files: dict(str)
        :param metadata: dictionnaire avec les méta-données
        :type metadata: dict(str)
        """
        files = {'etu': etu_path} if access == 'r' else None
        super().__init__(access, files, metadata)
        self.files['etu'] = etu_path  # FIXME: hack to overwrite the special key 'etu'
        self.access = access
        if folders is None:
            self.folders = Etude.FOLDERS
        else:
            if set(folders.keys()) != set(Etude.FOLDERS.keys()):
                raise RuntimeError
            if folders['FICHETUDES'] != '.':
                raise NotImplementedError
            self.folders = folders
        self.filename_list = []
        self.nom_scenario_courant = ''
        self.set_comment(comment)

        self.scenarios = OrderedDict()
        self.modeles = OrderedDict()
        self.sous_modeles = OrderedDict()

        if access == 'r':
            self._read_etu()
        elif access == 'w':
            pass
        else:
            raise NotImplementedError

    @property
    def etu_path(self):
        """Chemin vers le fichier Etude (*.etu.xml)"""
        return self.files['etu']

    @property
    def folder(self):
        return os.path.abspath(os.path.dirname(self.etu_path))

    def get_chemin_vers_fichier(self, filename):
        for fich_path in self.filename_list:
            if fich_path.endswith(filename):
                return fich_path
        raise ExceptionCrue10("Le fichier %s n'est pas dans la liste des fichiers !" % filename)

    def get_liste_run_names(self):
        """Liste des noms de Runs"""
        run_names = []
        for _, scenario in self.scenarios.items():
            run_names += scenario.runs.keys()
        return run_names

    def _read_etu(self):
        root = ET.parse(self.etu_path).getroot()
        folder = os.path.dirname(self.etu_path)

        # Etude metadata
        self.metadata = read_metadata(root, Etude.METADATA_FIELDS)

        if root.find(PREFIX + 'ScenarioCourant') is not None:
            self.nom_scenario_courant = root.find(PREFIX + 'ScenarioCourant').get('NomRef')

        # Repertoires
        elt_repertoires = root.find(PREFIX + 'Repertoires')
        for repertoire in elt_repertoires:
            self.folders[repertoire.get('Nom')] = repertoire.find(PREFIX + 'path').text

        # FichEtudes
        elt_fichiers = root.find(PREFIX + 'FichEtudes')
        for elt_fichier in elt_fichiers:
            if elt_fichier.get('Type').lower() in Etude.SUB_FILES_XML:  # Ignore Crue9 files
                if elt_fichier.get('Chemin') == '.\\':
                    norm_folder = os.path.normpath(folder)
                else:
                    norm_folder = os.path.normpath(os.path.join(folder, elt_fichier.get('Chemin')))
                fich_path = os.path.join(norm_folder, elt_fichier.get('Nom'))
                self.filename_list.append(fich_path)

        # SousModeles
        elt_sous_modeles = root.find(PREFIX + 'SousModeles')
        for elt_sm in elt_sous_modeles:
            files = {}
            nom_sous_modele = elt_sm.get('Nom')

            metadata = read_metadata(elt_sm, SousModele.METADATA_FIELDS)

            elt_fichiers = elt_sm.find(PREFIX + 'SousModele-FichEtudes')
            for ext in SousModele.FILES_XML:
                try:
                    filename = elt_fichiers.find(PREFIX + ext.upper()).attrib['NomRef']
                except AttributeError:
                    raise ExceptionCrue10("Le fichier %s n'est pas renseigné dans le sous-modèle !" % ext)
                if filename is None:
                    raise ExceptionCrue10("Le sous-modèle n'a pas de fichier %s !" % ext)
                files[ext] = self.get_chemin_vers_fichier(filename)

            for shp_name in SousModele.FILES_SHP:
                files[shp_name] = os.path.join(folder, self.folders['CONFIG'],
                                               nom_sous_modele.upper(), shp_name + '.shp')

            sous_modele = SousModele(nom_sous_modele, files=files, metadata=metadata)
            self.ajouter_sous_modele(sous_modele)
        if not self.sous_modeles:
            raise ExceptionCrue10("Il faut au moins un sous-modèle !")

        # Modele
        elt_models = root.find(PREFIX + 'Modeles')
        for elt_modele in elt_models:
            if elt_modele.tag == PREFIX + 'Modele':  # Ignore Crue9 modeles
                files = {}
                model_name = elt_modele.get('Nom')

                metadata = read_metadata(elt_modele, Modele.METADATA_FIELDS)

                elt_fichiers = elt_modele.find(PREFIX + 'Modele-FichEtudes')
                for ext in Modele.FILES_XML:
                    try:
                        filename = elt_fichiers.find(PREFIX + ext.upper()).attrib['NomRef']
                    except AttributeError:
                        raise ExceptionCrue10("Le fichier %s n'est pas renseigné dans le modèle !" % ext)
                    if filename is None:
                        raise ExceptionCrue10("Le modèle n'a pas de fichier %s !" % ext)
                    files[ext] = self.get_chemin_vers_fichier(filename)

                modele = Modele(model_name, files=files, metadata=metadata)

                elt_sous_modeles = elt_modele.find(PREFIX + 'Modele-SousModeles')
                for elt_sm in elt_sous_modeles:
                    nom_sous_modele = elt_sm.get('NomRef')
                    sous_modele = self.sous_modeles[nom_sous_modele]
                    modele.ajouter_sous_modele(sous_modele)

                self.ajouter_modele(modele)
        if not self.modeles:
            raise ExceptionCrue10("Il faut au moins un modèle !")

        # Scenarios
        elt_scenarios = root.find(PREFIX + 'Scenarios')
        for elt_scenario in elt_scenarios:
            if elt_scenario.tag == PREFIX + 'Scenario':
                files = {}
                nom_scenario = elt_scenario.get('Nom')

                elt_fichiers = elt_scenario.find(PREFIX + 'Scenario-FichEtudes')
                for ext in Scenario.FILES_XML:
                    try:
                        filename = elt_fichiers.find(PREFIX + ext.upper()).attrib['NomRef']
                    except AttributeError:
                        raise ExceptionCrue10("Le fichier %s n'est pas renseigné dans le scénario !" % ext)
                    if filename is None:
                        raise ExceptionCrue10("Le scénario n'a pas de fichier %s !" % ext)
                    files[ext] = self.get_chemin_vers_fichier(filename)

                elt_models = elt_scenario.find(PREFIX + 'Scenario-Modeles')
                modele = None
                for i, elt_modele in enumerate(elt_models):
                    modele = self.modeles[elt_modele.get('NomRef')]
                    if i != 0:
                        raise NotImplementedError  # A single Modele for a Scenario!

                metadata = read_metadata(elt_scenario, Scenario.METADATA_FIELDS)
                scenario = Scenario(nom_scenario, modele, files=files, metadata=metadata)

                runs = elt_scenario.find(PREFIX + 'Runs')
                if runs is not None:
                    for run_elt in runs:
                        run_id = run_elt.get('Nom')
                        metadata = read_metadata(run_elt, Run.METADATA_FIELDS)
                        run_mo_path = os.path.join(self.folder, self.folders['RUNS'], scenario.id,
                                                     run_id, scenario.modele.id)
                        scenario.add_run(Run(run_mo_path, metadata=metadata))

                elt_current_run = elt_scenario.find(PREFIX + 'RunCourant')
                if elt_current_run is not None:
                    scenario.set_current_run_id(elt_current_run.get('NomRef'))

                self.ajouter_scenario(scenario)

        if not self.scenarios:
            raise ExceptionCrue10("Il faut au moins un scénario !")

    def read_all(self):
        """Lire tous les fichiers de l'étude"""
        # self._read_etu() is done in `__init__` method
        for _, scenario in self.scenarios.items():
            scenario.read_all()

    def write_etu(self, folder=None):
        """Écriture du fichier Etude Crue10 (*.etu.xml)

        Si folder n'est pas renseigné alors le fichier lu est remplacé
        """
        if folder is None:
            etu_path = os.path.join(self.folder, os.path.basename(self.etu_path))
        else:
            etu_path = os.path.join(folder, os.path.basename(self.etu_path))
        xml = 'etu'
        template_render = JINJA_ENV.get_template(xml + '.xml').render(
            folders=[(name, folder_str) for name, folder_str in self.folders.items()],
            metadata=self.metadata,
            current_scenario_id=self.nom_scenario_courant,
            files=[(os.path.basename(file), file[-8:-4].upper()) for file in sorted(self.filename_list)],
            modeles=[mo for _, mo in self.modeles.items()],
            sous_modeles=[sm for _, sm in self.sous_modeles.items()],
            scenarios=[sc for _, sc in self.scenarios.items()],
        )
        with open(etu_path, 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

    def write_all(self, folder=None, ignore_shp=False):
        """Écrire tous les fichiers de l'étude"""
        folder = self.folder if folder is None else folder
        logger.debug("Écriture de l'%s dans %s" % (self, folder))

        # Create folder if not existing
        if not os.path.exists(folder):
            os.makedirs(folder)

        self.write_etu(folder)

        if ignore_shp:
            folder_config = None
        else:
            folder_config = self.folders['CONFIG']
        for _, scenario in self.scenarios.items():
            scenario.write_all(folder, folder_config)

    def add_files(self, file_list):
        for file in file_list:
            if file not in self.filename_list:
                self.filename_list.append(file)

    def ajouter_modele(self, modele):
        """Ajouter un modèle à l'étude

        :param modele: modèle à ajouter
        :type modele: Modele
        """
        check_isinstance(modele, Modele)
        # if modele.id in self.modeles:
        #     raise ExceptionCrue10("Le modèle %s est déjà présent" % modele.id)
        self.add_files([file for _, file in modele.files.items()])
        for sous_modele in modele.liste_sous_modeles:
            self.ajouter_sous_modele(sous_modele)
        self.modeles[modele.id] = modele

    def ajouter_sous_modele(self, sous_modele):
        """Ajouter un sous-modèle à l'étude

        :param sous_modele: sous-modèle à ajouter
        :type sous_modele: SousModele
        """
        check_isinstance(sous_modele, SousModele)
        # if sous_modele.id in self.sous_modeles:
        #     raise ExceptionCrue10("Le sous-modèle %s est déjà présent" % sous_modele.id)
        self.add_files([file for _, file in sous_modele.files.items() if file[-8:-4] in SousModele.FILES_XML])
        self.sous_modeles[sous_modele.id] = sous_modele

    def ajouter_scenario(self, scenario):
        """Ajouter un scénario à l'étude

        :param scenario: scénario à ajouter
        :type scenario: Scenario
        """
        check_isinstance(scenario, Scenario)
        if scenario.id in self.scenarios:
            raise ExceptionCrue10("Le scénario %s est déjà présent" % scenario.id)
        self.add_files([file for _, file in scenario.files.items()])
        self.ajouter_modele(scenario.modele)
        self.scenarios[scenario.id] = scenario

    def create_empty_scenario(self, nom_scenario, nom_modele, nom_sous_modele=None, comment=''):
        """
        Créer scénario vierge (avec son modèle et sous-modèle associé)

        :param nom_scenario: nom du scénario
        :param nom_modele: nom du modèle
        :param nom_sous_modele: nom du sous-modèle (optionnel)
        :param comment: commentaire (optionnel)
        """
        modele = Modele(nom_modele, access=self.access, metadata={'Commentaire': comment})
        if nom_sous_modele is not None:
            sous_modele = SousModele(nom_sous_modele, access=self.access, metadata={'Commentaire': comment})
            modele.ajouter_sous_modele(sous_modele)
        scenario = Scenario(nom_scenario, modele, access=self.access, metadata={'Commentaire': comment})
        self.ajouter_scenario(scenario)
        if not self.nom_scenario_courant:
            self.nom_scenario_courant = scenario.id

    def get_scenario(self, nom_scenario):
        """
        Retourne le scénario demandé

        :param nom_scenario: nom du scénario demandé
        """
        try:
            return self.scenarios[nom_scenario]
        except KeyError:
            raise ExceptionCrue10("Le scénario %s n'existe pas !\nLes noms possibles sont: %s"
                                  % (nom_scenario, list(self.scenarios.keys())))

    def get_scenario_courant(self):
        """Retourne le scénario courant"""
        if self.nom_scenario_courant:
            return self.get_scenario(self.nom_scenario_courant)
        raise ExceptionCrue10("Aucun scénario courant n'est défini dans l'étude")

    def get_modele(self, nom_modele):
        """
        Retourne le modèle demandé

        :param nom_modele: nom du modèle demandé
        """
        try:
            return self.modeles[nom_modele]
        except KeyError:
            raise ExceptionCrue10("Le modèle %s n'existe pas !\nLes noms possibles sont: %s"
                                  % (nom_modele, list(self.modeles.keys())))

    def get_sous_modele(self, nom_sous_modele):
        """
        Retourne le sous-modèle demandé

        :param nom_sous_modele: nom du sous-modèle demandé
        """
        try:
            return self.sous_modeles[nom_sous_modele]
        except KeyError:
            raise ExceptionCrue10("Le sous-modèle %s n'existe pas !\nLes noms possibles sont: %s"
                                  % (nom_sous_modele, list(self.sous_modeles.keys())))

    def get_liste_scenarios(self):
        return [scenario for _, scenario in self.scenarios.items()]

    def get_liste_modeles(self):
        return [modele for _, modele in self.modeles.items()]

    def get_liste_sous_modeles(self):
        return [sous_modele for _, sous_modele in self.sous_modeles.items()]

    def ajouter_scenario_par_copie(self, nom_scenario_source, nom_scenario_cible):
        """
        Copie d'un scénario existant et ajout à l'étude courante
        Attention le modèle et les sous-modèles restent partagés avec le scénario source
        Les Runs existants ne sont pas copiés dans le scénario cible
        Remarque : une copie profonde n'est pas possible car il faudrait renommer le modèle et les sous-modèles...
        """
        scenario_ori = self.get_scenario(nom_scenario_source)
        scenario = Scenario(nom_scenario_cible, scenario_ori.modele, access='w',
                            files=scenario_ori.files, metadata=scenario_ori.metadata)
        scenario.read_all()
        self.ajouter_scenario(scenario)
        return scenario

    def ignore_others_scenarios(self, nom_scenario):
        scenario_to_keep = self.get_scenario(nom_scenario)
        filepath_to_keep = []  # to purge FichEtudes/FichEtude

        for scenario in self.get_liste_scenarios():
            if scenario is scenario_to_keep:
                filepath_to_keep += [filename for _, filename in scenario.files.items()]
            else:
                del self.scenarios[scenario.id]

        for modele in self.get_liste_modeles():
            if modele is scenario_to_keep.modele:
                filepath_to_keep += [filename for _, filename in modele.files.items()]
            else:
                del self.modeles[modele.id]

        for sous_modele in self.get_liste_sous_modeles():
            if sous_modele in scenario_to_keep.modele.liste_sous_modeles:
                filepath_to_keep += [filename for _, filename in sous_modele.files.items()]
            else:
                del self.sous_modeles[sous_modele.id]

        for filename in deepcopy(self.filename_list):
            file_path = os.path.join(filename)
            if file_path not in filepath_to_keep:
                self.filename_list.remove(filename)

    def supprimer_scenario(self, nom_scenario, ignore=False, sleep=0.0):
        logger.info("Suppression du scénario %s" % nom_scenario)
        if not ignore:
            # Check that is exists if required
            self.get_scenario(nom_scenario)

        try:
            del self.scenarios[nom_scenario]
        except KeyError:  # ignore if not found
            pass

        # Remove Runs folder once to speedup the deletion and remove potential orphan runs
        # instead of simply calling scenario.remove_all_runs()
        run_folder = os.path.join(self.folder, self.folders['RUNS'], nom_scenario)
        if os.path.exists(run_folder):
            rmtree(run_folder)
        if sleep > 0.0:  # Avoid potential conflict if folder is rewritten directly afterwards
            time.sleep(sleep)

    def check_xml_files(self, folder=None):
        """Validation des fichiers XML à partir des schémas XSD"""
        errors = {}
        for file_path in self.filename_list:
            errors[file_path] = self._check_xml_file(file_path)
        return errors

    def summary(self):
        return "%s: %i scénario(s) %i modèle(s), %i sous-modèle(s)" % (self, len(self.scenarios),
                                                                       len(self.modeles), len(self.sous_modeles))

    def __repr__(self):
        return "Étude %s" % os.path.basename(self.etu_path[:-8])
