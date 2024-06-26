# coding: utf-8
import abc
from copy import deepcopy
from io import open  # Python2 fix
import os.path
import xml.etree.ElementTree as ET

from crue10.utils import add_default_missing_metadata, check_xml_file, DATA_FOLDER_ABSPATH, ExceptionCrue10, \
    ExceptionCrue10Grammar, JINJA_ENV, get_xml_root_from_file, logger, PREFIX, XSI_SCHEMA_LOCATION
from crue10.utils.settings import VERSION_GRAMMAIRE_COURANTE, VERSION_GRAMMAIRE_PRECEDENTE, XML_ENCODING


# ABC below is compatible with Python 2 and 3
ABC = abc.ABCMeta('ABC', (object,), {'__slots__': ()})


class EnsembleFichiersXML(ABC):
    """
    Classe abstraite pour les fichiers XML Crue10

    :ivar version_grammaire: version de la grammaire
    :vartype version_grammaire: str
    :ivar xml_trees: dictionnaire avec les arbres XML (les clés correspondent à `FILES_XML_WITHOUT_TEMPLATE`)
    :vartype xml_trees: {ET.ElementTree}
    :ivar metadata: dictionnaire avec les méta-données (les clés correspondent à `METADATA_FIELDS`)
    :vartype metadata: {dict}
    :ivar files: dictionnaire avec les chemins vers les fichiers XML (les clés correspondent à `FILES_XML` list)
    :vartype files: {str}
    :ivar comments: dictionnaire avec les commentaires en en-tête des fichiers XML (les clés correspondent à `FILES_XML` list)
    :vartype comments: {str}
    :ivar was_read: True si déjà lu
    :vartype was_read: bool
    """

    #: Fichiers XML
    FILES_XML = []

    #: Sous-fichiers XML pour Etude (l'ensemble des types composant une étude Crue10)
    SUB_FILES_XML = []

    #: Fichiers SHP pour SousModele
    FILES_SHP = []

    #: Fichiers XML sans template jinja2 (le fichier est lu/écrit par l'utilisation d'un simple parseur XML)
    FILES_XML_WITHOUT_TEMPLATE = []

    #: Nom des métadonnées présentes dans le fichier etu.xml
    METADATA_FIELDS = []

    def __init__(self, mode, files, metadata, version_grammaire=None):
        """
        L'attribut `id` doit être défini avant d'appeler cette méthode mère (super)
        """
        self.xml_trees = {}

        self.metadata = {} if metadata is None else metadata
        if 'Type' in type(self).METADATA_FIELDS:
            self.metadata['Type'] = 'Crue10'
        self.metadata = add_default_missing_metadata(self.metadata, type(self).METADATA_FIELDS)

        self.version_grammaire = version_grammaire
        if mode == 'r':
            if files is None:
                raise RuntimeError

            files_xml = deepcopy(type(self).FILES_XML)
            if version_grammaire == '1.2':  # Modele: HARDCODED to support g1.2
                try:
                    files_xml.remove('dreg')
                except ValueError:  # Etude, Scenario, SousModele
                    pass
            if set(files.keys()) != set(files_xml + type(self).FILES_SHP):
                raise RuntimeError
            self.files = files
            self.was_read = False

        elif mode == 'w':
            if version_grammaire is None:
                self.version_grammaire = VERSION_GRAMMAIRE_COURANTE
            self.files = {}
            if files is None:
                for xml_type in type(self).FILES_XML:
                    if xml_type != 'etu':
                        self.files[xml_type] = self.id[3:] + '.' + xml_type + '.xml'
            else:
                self.files = files
            if version_grammaire == '1.2':  # Modele: HARDCODED to support g1.2
                try:
                    self.files.pop('dreg')
                except KeyError:  # Etude, Scenario, SousModele
                    pass
            self.was_read = True

        self.comments = {xml: '' for xml in type(self).FILES_XML}

    @property
    def is_active(self):
        """Est actif"""
        return self.metadata['IsActive'] == 'true'

    @property
    def comment(self):
        """Commentaire"""
        return self.metadata['Commentaire']

    @property
    def file_basenames(self):
        """Retourne la liste des fichiers par type"""
        return {xml_type: os.path.basename(path) for xml_type, path in self.files.items()}

    def set_version_grammaire(self, version_grammaire):
        """
        Définir la version de la grammaire

        :param version_grammaire: version de la grammaire à définir
        :type version_grammaire: str
        """
        # Check version_grammaire consistency
        grammaires_supportees = [VERSION_GRAMMAIRE_PRECEDENTE, VERSION_GRAMMAIRE_COURANTE]
        if version_grammaire not in grammaires_supportees:
            raise ExceptionCrue10Grammar("Seules les grammaires %s sont supportées (pas `%s`)"
                                         % (grammaires_supportees, version_grammaire))
        if version_grammaire == self.version_grammaire:
            logger.warning("Changement de grammaire vers %s ignoré car %s est déjà dans cette grammaire"
                           % (version_grammaire, self))
            return  # nothing to do

        self.version_grammaire = version_grammaire

    def changer_version_grammaire(self, version_grammaire, shallow=False):
        """
        Changer la version de la grammaire

        :param version_grammaire: version de la grammaire cible
        :type version_grammaire: str
        :param shallow: conversion profonde si False, peu profonde sinon
        :type shallow: bool
        """
        if not self.was_read and not self.xml_trees:
            raise ExceptionCrue10("%s doit être lu (avec la méthode `read_all`) avant de changer sa grammaire" % self)

        # Change version_grammaire in all `FILES_WITHOUT_TEMPLATE`
        for xml_type, root in self.xml_trees.items():
            old_xsi = root.get(XSI_SCHEMA_LOCATION)
            new_xsi = old_xsi.replace('-%s.xsd' % self.version_grammaire, '-%s.xsd' % version_grammaire)
            root.set(XSI_SCHEMA_LOCATION, new_xsi)

        self.set_version_grammaire(version_grammaire)

    def set_comment(self, comment):
        """Définir le commentaire"""
        self.metadata['Commentaire'] = comment

    def _get_xml_root_set_version_grammaire_and_comment(self, xml):
        try:
            root = ET.parse(self.files[xml]).getroot()
        except FileNotFoundError:
            raise ExceptionCrue10("Fichier introuvable: %s" % self.files[xml])
        except ET.ParseError as e:
            raise ExceptionCrue10("Erreur syntaxe XML dans `%s`:\n%s" % (self.files[xml], e))

        # Set version_grammaire
        version_grammaire = root.get(XSI_SCHEMA_LOCATION)[-7:-4]
        if self.version_grammaire is None:
            self.set_version_grammaire(version_grammaire)
        elif version_grammaire != self.version_grammaire:
            raise ExceptionCrue10Grammar("La version de la grammaire du fichier %s est %s (valeur attendue : %s)"
                                         % (xml, version_grammaire, self.version_grammaire))

        # Sets comment if the tag is found
        comment_elt = root.find(PREFIX + 'Commentaire')
        if comment_elt is not None:
            self.comments[xml] = '' if comment_elt.text is None else comment_elt.text

        return root

    def _set_xml_trees(self):
        files_xml = deepcopy(type(self).FILES_XML_WITHOUT_TEMPLATE)
        if self.version_grammaire == '1.2':  # Modele: HARDCODED to support g1.2
            try:
                files_xml.remove('dreg')
            except ValueError:  # Scenario
                pass
        for xml_type in files_xml:
            try:
                root = get_xml_root_from_file(self.files[xml_type])
            except KeyError:
                raise ExceptionCrue10("Le fichier `%s` est absent !" % xml_type)

            # Set version_grammaire
            version_grammaire = root.get(XSI_SCHEMA_LOCATION)[-7:-4]
            if self.version_grammaire is None:
                self.set_version_grammaire(version_grammaire)
            elif version_grammaire != self.version_grammaire:
                raise ExceptionCrue10Grammar(
                    "La version de la grammaire du fichier %s est %s (valeur attendue : %s)"
                    % (xml_type, version_grammaire, self.version_grammaire))

            self.xml_trees[xml_type] = root

    def _write_xml_file(self, xml, folder, **kwargs):
        template_path = self.version_grammaire + '/templates/' + xml + '.xml'  # os.path.join not working on Windows
        template_render = JINJA_ENV.get_template(template_path).render(
            comment=self.comments[xml],
            **kwargs
        )

        with open(os.path.join(folder, os.path.basename(self.files[xml])), 'w', encoding=XML_ENCODING) as out:
            out.write(template_render)

    def _check_xml_file(self, file_path):
        return check_xml_file(file_path, self.version_grammaire)

    def check_xml_files(self, folder=None):
        """
        Validation XML des fichiers à leur schéma XSD

        :return: liste des erreurs
        :rtype: list(str)
        """
        if folder is None:
            filename_list = [filename for _, filename in self.files.items()]
        else:
            filename_list = [os.path.join(folder, filename) for _, filename in self.files.items()]
        errors = {}
        for file_path in filename_list:
            errors[os.path.basename(file_path)] = self._check_xml_file(file_path)
        return errors

    def log_check_xml(self, folder=None):
        """Afficher le bilan de la vérification des fichiers XML"""
        errors = self.check_xml_files(folder)
        nb_errors = 0
        for xml_file, liste_errors in errors.items():
            if liste_errors:
                logger.error("~> %i erreur(s) dans %s:" % (len(liste_errors), os.path.basename(xml_file)))
                for i, error in enumerate(liste_errors):
                    logger.error("    #%i: %s" % (i + 1, error))
                nb_errors += len(liste_errors)
        if nb_errors == 0:
            logger.info("=> Aucune erreur dans les fichiers XML (pour %s)" % self)
        else:
            logger.error("=> %i erreur(s) dans les fichiers XML" % nb_errors)
