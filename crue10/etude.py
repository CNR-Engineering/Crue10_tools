# coding: utf-8
from builtins import super  # Python2 fix
from collections import OrderedDict
from io import open  # Python2 fix
import os.path
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
    """
    Crue10 etude
    - access <str>: 'r' to read and 'w' to write
    - folders <{str}>: dict with folders (keys correspond to `FOLDERS` list)
    - filename_list <[str]>: list of xml file names
    - nom_scenario_courant <str>: current scenario identifier
    - scenarios <{str: Scenario}>: dict with scneario name and Scenario object
    - modeles <{str: Modele}>: dict with modele name and Modele object
    - liste_sous_modeles <{str: SousModele}>: dict with sous_modele name and SousModele object
    """

    FOLDERS = OrderedDict([('CONFIG', 'Config'), ('FICHETUDES', '.'),
                           ('RAPPORTS', 'Rapports'), ('RUNS', 'Runs')])
    FILES_XML = ['etu']
    SUB_FILES_XML = Scenario.FILES_XML + Modele.FILES_XML + SousModele.FILES_XML
    METADATA_FIELDS = ['Commentaire', 'AuteurCreation', 'DateCreation', 'AuteurDerniereModif', 'DateDerniereModif']

    def __init__(self, etu_path, folders=None, access='r', metadata=None, comment=''):
        """
        :param etu_path: Crue10 etude file (etu.xml format)
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
        # self._read_etu() is done in `__init__` method
        for _, scenario in self.scenarios.items():
            scenario.read_all()

    def write_etu(self, folder=None):
        """If folder is not given, the file is overwritten"""
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

    def write_all(self, folder=None):
        folder = self.folder if folder is None else folder
        logger.debug("Écriture de l'%s dans %s" % (self, folder))

        # Create folder if not existing
        if not os.path.exists(folder):
            os.makedirs(folder)

        self.write_etu(folder)
        for _, scenario in self.scenarios.items():
            scenario.write_all(folder, self.folders['CONFIG'])

    def add_files(self, file_list):
        for file in file_list:
            if file not in self.filename_list:
                self.filename_list.append(file)

    def ajouter_modele(self, modele):
        check_isinstance(modele, Modele)
        self.add_files([file for _, file in modele.files.items()])
        for sous_modele in modele.liste_sous_modeles:
            self.ajouter_sous_modele(sous_modele)
        self.modeles[modele.id] = modele

    def ajouter_sous_modele(self, sous_modele):
        check_isinstance(sous_modele, SousModele)
        self.add_files([file for _, file in sous_modele.files.items() if file[-8:-4] in SousModele.FILES_XML])
        self.sous_modeles[sous_modele.id] = sous_modele

    def ajouter_scenario(self, scenario):
        check_isinstance(scenario, Scenario)
        self.add_files([file for _, file in scenario.files.items()])
        self.ajouter_modele(scenario.modele)
        self.scenarios[scenario.id] = scenario

    def create_empty_scenario(self, nom_scenario, nom_modele, nom_sous_modele=None, comment=''):
        modele = Modele(nom_modele, access=self.access, metadata={'Commentaire': comment})
        if nom_sous_modele is not None:
            sous_modele = SousModele(nom_sous_modele, access=self.access, metadata={'Commentaire': comment})
            modele.ajouter_sous_modele(sous_modele)
        scenario = Scenario(nom_scenario, modele, access=self.access, metadata={'Commentaire': comment})
        self.ajouter_scenario(scenario)
        if not self.nom_scenario_courant:
            self.nom_scenario_courant = scenario.id

    def get_scenario(self, scenario_name):
        try:
            return self.scenarios[scenario_name]
        except KeyError:
            raise ExceptionCrue10("Le scénario %s n'existe pas !\nLes noms possibles sont: %s"
                                  % (scenario_name, list(self.scenarios.keys())))

    def get_scenario_courant(self):
        if self.nom_scenario_courant:
            return self.get_scenario(self.nom_scenario_courant)
        raise ExceptionCrue10("Aucun scénario courant n'est défini dans l'étude")

    def get_modele(self, nom_modele):
        try:
            return self.modeles[nom_modele]
        except KeyError:
            raise ExceptionCrue10("Le modèle %s n'existe pas !\nLes noms possibles sont: %s"
                                  % (nom_modele, list(self.modeles.keys())))

    def get_sous_modele(self, nom_sous_modele):
        try:
            return self.sous_modeles[nom_sous_modele]
        except KeyError:
            raise ExceptionCrue10("Le sous-modèle %s n'existe pas !\nLes noms possibles sont: %s"
                                  % (nom_sous_modele, list(self.sous_modeles.keys())))

    def check_xml_files(self, folder=None):
        errors = {}
        for file_path in self.filename_list:
            errors[file_path] = self._check_xml_file(file_path)
        return errors

    def summary(self):
        return "%s: %i scénario(s) %i modèle(s), %i sous-modèle(s)" % (self, len(self.scenarios),
                                                                       len(self.modeles), len(self.sous_modeles))

    def __repr__(self):
        return "Étude %s" % os.path.basename(self.etu_path[:-8])
