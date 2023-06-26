# coding: utf-8
from collections import OrderedDict
import csv
import io  # Python2 fix
import numpy as np
import os.path
import pandas as pd
import re
import struct
from sys import version_info
import xml.etree.ElementTree as ET

from crue10.utils import ExceptionCrue10, PREFIX
from crue10.utils.settings import CSV_DELIMITER, FMT_FLOAT_CSV


#: Regex pour le format des durées de Crue10
TIME_REGEX = re.compile(r'P(?P<days>[0-9]+)DT(?P<hours>[0-9]+)H(?P<mins>[0-9]+)M(?P<secs>[0-9]+)S')


def get_time_in_seconds(time_str):
    """
    Convertir une durée au format Crue10 en secondes

    :param time_str: durée au format Crue10
    :type time_str: str
    :rtype: float
    """
    match = TIME_REGEX.match(time_str)
    values = {duration: int(counter) for duration, counter in match.groupdict().items()}
    return ((values['days'] * 24 + values['hours']) * 60 + values['mins']) * 60 + values['secs']


class FilePosition:
    """
    Fichier binaire est en "little endian" avec des valeurs sur 8 bytes
    (ie. double precision pour les valeurs numériques)

    :ivar rbin_path: chemin complet vers le fichier RBIN
    :vartype rbin_path: str
    :ivar byte_offset: position dans le fichier
    :vartype byte_offset: int
    """
    #: Encodage des chaînes de caractères
    ENCODING = 'utf-8'

    #: Nombre de bytes pour représenter un flottant
    FLOAT_SIZE = 8

    #: Précision des flottants
    FLOAT_TYPE = 'd'

    def __init__(self, rbin_path, byte_offset):
        """
        :param rbin_path: chemin complet vers le fichier RBIN
        :type rbin_path: str
        :param byte_offset: position dans le fichier
        :type byte_offset: int
        """
        self.rbin_path = rbin_path
        self.byte_offset = byte_offset

    def get_data(self, res_pattern, is_pseudoperm, emh_type_first_branche):
        """
        :param res_pattern: schéma d'organisation des résultats. Par exemple [('Noeud', (120, 1)), ('Casier', (48, 4)),
            ('Section', (593, 8)), ('BrancheBarrageFilEau', (1, 1)), ...]
        :type res_pattern: list(tuple(str, (int, int)))
        :param is_pseudoperm: les données correspondent à un calcul pseudo-permanent
            (pour vérifier la cohérence d'un délimiteur)
        :type is_pseudoperm: bool
        :param emh_type_first_branche: premier type d'EMH secondaire pour Branche (pa ex. 'BrancheBarrageFilEau')
        :type emh_type_first_branche: str
        :return: dictionnaire avec les types d'EMH secondaires et le tableau de données (shape=(nb_emh, nb_var))
        :rtype: dict(np.ndarray)
        """
        res = {}
        with io.open(self.rbin_path, 'rb') as resin:
            resin.seek(self.byte_offset * FilePosition.FLOAT_SIZE)

            # Check calculation type
            calc_delimiter = resin.read(FilePosition.FLOAT_SIZE).decode(FilePosition.ENCODING).strip()
            if is_pseudoperm:
                if calc_delimiter != 'RcalPp':
                    raise ExceptionCrue10("Le calcul n'est pas permanent !")
            else:
                if calc_delimiter != 'RcalPdt':
                    raise ExceptionCrue10("Le calcul n'est pas transitoire !")

            for emh_type, (nb_emh, nb_var) in res_pattern:
                if not emh_type.startswith('Branche') or emh_type == emh_type_first_branche:
                    emh_delimiter = resin.read(FilePosition.FLOAT_SIZE).decode(FilePosition.ENCODING).strip()
                    if emh_delimiter not in emh_type:
                        raise ExceptionCrue10("Les EMH attendus sont %s (au lieu de %s)" % (emh_type, emh_delimiter))
                values = struct.unpack('<' + str(nb_emh * nb_var) + FilePosition.FLOAT_TYPE,
                                       resin.read(nb_emh * nb_var * FilePosition.FLOAT_SIZE))
                res[emh_type] = np.array(values).reshape((nb_emh, nb_var))
        return res


class ResCalcPseudoPerm:
    """
    Métadonnées des résultats pour un calcul pseudo-permanent

    :ivar name: nom du calcul pseudo-permanent
    :vartype name: str
    :ivar file_pos: position dans les fichiers RBIN
    :vartype file_pos: FilePosition
    """

    def __init__(self, name, bin_path, byte_offset):
        """
        :param name: nom du calcul pseudo-permanent
        :type name: str
        :param bin_path: chemin complet vers le fichier RBIN
        :type bin_path: str
        :param byte_offset: position dans le fichier
        :type byte_offset: int
        """
        self.name = name
        self.file_pos = FilePosition(bin_path, byte_offset)

    def __repr__(self):
        return "Calcul permanent #%s" % self.name


class ResCalcTrans:
    """
    Métadonnées des résultats pour un calcul transitoire

    XXX
    """

    def __init__(self, name):
        self.name = name
        self.frame_list = []

    def add_frame(self, time_sec, bin_path, byte_offset):
        self.frame_list.append((time_sec, FilePosition(bin_path, byte_offset)))

    def time_serie(self):
        return np.array([frame[0] for frame in self.frame_list])

    def __repr__(self):
        return "Calcul non permanent #%s (%i temps)" % (self.name, len(self.frame_list))


class ResultatsCalcul:
    """
    Données résultats de calcul d'un Run

    :ivar rcal_root: racine de l'élément XML rcal
    :vartype rcal_root: ET.etree._Element
    :ivar rcal_path: chemin vers le fichier rcal
    :vartype rcal_path: str
    :ivar rcal_folder: chemin vers le dossier du fichier rcal
    :vartype rcal_folder: str
    :ivar emh_types: liste des types d'EMH secondaires,
        par exemple : ['Noeud', 'Casier', 'Section', 'BrancheBarrageFilEau', 'BrancheOrifice', 'BrancheSaintVenant'...]
    :vartype emh_types: list(str)
    :ivar emh: dictionnaires avec les types d'EMH secondaires donnant la liste des EMHs disponibles
    :vartype emh: OrderedDict(str)
    :ivar variables: dictionnaires avec les types d'EMH secondaires donnant la liste des variables disponibles
    :vartype variables: OrderedDict(str)
    :ivar variables_Qregul: liste des variables Qregul
    :vartype variables_Qregul: list(str)
    :ivar variables_Zregul: liste des variables Zregul
    :vartype variables_Zregul: list(str)
    :ivar res_calc_pseudoperm: dictionnaires avec les métadonnées des calculs pseudo-permanents
    :vartype res_calc_pseudoperm: OrderedDict(ResCalcPseudoPerm)
    :ivar res_calc_trans: dictionnaires avec les métadonnées des calculs transitoires
    :vartype res_calc_trans: OrderedDict(ResCalcTrans)
    :ivar _emh_type_first_branche: premier type d'EMH "secondaire" pour Branche (pa ex. 'BrancheBarrageFilEau')
    :vartype _emh_type_first_branche: str
    :ivar _res_pattern: liste de tuples du type (emh_type, shape)
    :vartype _res_pattern: list(tuple)
    """
    #: Noms des EMHs primaires
    EMH_PRIMARY_TYPES = ['Noeud', 'Casier', 'Section', 'Branche', 'Modele']

    def __init__(self, rcal_path):
        """
        :param rcal_path: chemin vers le fichier rcal
        :type rcal_path: str
        """
        self.rcal_root = ET.parse(rcal_path).getroot()
        self.rcal_path = rcal_path
        self.rcal_folder = os.path.dirname(rcal_path)
        self.emh_types = []
        self.emh = OrderedDict()
        self.variables = OrderedDict()
        self.variables_Qregul = []
        self.variables_Zregul = []
        self.res_calc_pseudoperm = OrderedDict()
        self.res_calc_trans = OrderedDict()

        self._emh_type_first_branche = None
        self._res_pattern = []

        self._read_parametrage()
        self._read_structure()
        self._read_rescalc()
        self._set_res_pattern()

    @property
    def run_id(self):
        """Nom du run"""
        return os.path.basename(os.path.normpath(os.path.join(self.rcal_folder, '..')))

    def _add_variables_names(self, elt, emh_sec):
        """
        Ajout des variables pour ce type d'EMHs

        :param elt: élément XML
        :rtype elt: xml.etree.ElementTree.Element
        :param emh_sec: type d'EMHs
        :rtype emh_sec: str
        """
        if emh_sec not in self.variables:
            self.variables[emh_sec] = []
        for sub_elt in elt:
            varname = sub_elt.get('NomRef')
            if sub_elt.tag.endswith('VariableRes'):
                self.variables[emh_sec].append(varname)
            elif sub_elt.tag.endswith('VariableResQregul'):
                self.variables_Qregul.append(varname)
            elif sub_elt.tag.endswith('VariableResZregul'):
                self.variables_Zregul.append(varname)

    def _add_emh_names(self, elt, emh_sec):
        if int(elt.get('NbrMot')) > 0:  # Avoid empty lists in self.emh
            if emh_sec not in self.emh:
                if emh_sec.startswith('Branche') and self._emh_type_first_branche is None:
                    self._emh_type_first_branche = emh_sec
                self.emh_types.append(emh_sec)
                self.emh[emh_sec] = []
            for sub_elt in elt:
                if not sub_elt.tag.endswith('VariableRes') and not sub_elt.tag.endswith('VariableResQregul') \
                        and not sub_elt.tag.endswith('VariableResZregul'):
                    emh_name = sub_elt.get('NomRef')
                    self.emh[emh_sec].append(emh_name)

    def _read_parametrage(self):
        nb_bytes = int(self.rcal_root.find(PREFIX + 'Parametrage').find(PREFIX + 'NbrOctetMot').text)
        if nb_bytes != FilePosition.FLOAT_SIZE:
            raise ExceptionCrue10("La taille des données (%i octets) n'est pas supportée" % nb_bytes)

    def _read_structure(self):
        """
        Les EMH sont lues à partir des xpaths suivants :

        - `Noeuds/NoeudNiveauContinu/Noeud`
        - `Casiers/CasierProfil/Casier`
        - `Sections/{SectionIdem,SectionInterpolee,SectionProfil,SectionSansGeometrie}/Section` (mêmes variables)
        - `Branches/Branche*/Branche`
        """
        for emh_list in self.rcal_root.find(PREFIX + 'StructureResultat'):
            emh_type = emh_list.tag[len(PREFIX):-1]

            if emh_type == 'Branche':
                for sub_elt in emh_list:
                    emh_subtype = sub_elt.tag[len(PREFIX):]
                    self._add_variables_names(sub_elt, emh_subtype)
                    if not sub_elt.tag.endswith('VariableRes'):
                        self._add_emh_names(sub_elt, emh_subtype)
            else:
                if emh_type == 'Modele':
                    self._add_variables_names(emh_list.find(PREFIX + 'ModeleRegul'), 'Modele')
                    self._add_emh_names(emh_list.find(PREFIX + 'ModeleRegul'), 'Modele')
                elif emh_type == 'Noeud':
                    self._add_variables_names(emh_list.find(PREFIX + 'NoeudNiveauContinu'), 'Noeud')
                    self._add_emh_names(emh_list.find(PREFIX + 'NoeudNiveauContinu'), 'Noeud')
                elif emh_type == 'Casier':
                    self._add_variables_names(emh_list, 'Casier')
                    self._add_emh_names(emh_list.find(PREFIX + 'CasierProfil'), 'Casier')
                elif emh_type == 'Section':
                    self._add_variables_names(emh_list, 'Section')
                    for sub_elt in emh_list:
                        if not sub_elt.tag.endswith('VariableRes'):
                            self._add_emh_names(sub_elt, 'Section')

    def _read_rescalc(self):
        for calc in self.rcal_root.find(PREFIX + 'ResCalcPerms'):
            calc_pseudoperm = ResCalcPseudoPerm(calc.get('NomRef'), os.path.join(self.rcal_folder, calc.get('Href')),
                                                int(calc.get('OffsetMot')))
            self.res_calc_pseudoperm[calc_pseudoperm.name] = calc_pseudoperm

        for calc in self.rcal_root.find(PREFIX + 'ResCalcTranss'):
            calc_trans = ResCalcTrans(calc.get('NomRef'))
            for pdt in calc:
                calc_trans.add_frame(get_time_in_seconds(pdt.get('TempsSimu')),
                                     os.path.join(self.rcal_folder, pdt.get('Href')), int(pdt.get('OffsetMot')))
            self.res_calc_trans[calc_trans.name] = calc_trans

    def _set_res_pattern(self):
        emh_types_with_res = []
        for emh_type in self.emh_types:
            emh_types_with_res.append(emh_type)
            nbvar = len(self.variables[emh_type])
            if emh_type == 'Modele':
                nbvar += len(self.variables_Qregul) + len(self.variables_Zregul)
            self._res_pattern.append((emh_type, (len(self.emh[emh_type]), nbvar)))
        # Add emh_types which have no result data (because delimiter is still present)
        for i, emh_type in enumerate(ResultatsCalcul.EMH_PRIMARY_TYPES[:-1]):
            if emh_type not in emh_types_with_res:
                self._res_pattern.insert(i, (emh_type, (0, 0)))

    def emh_type(self, emh_name):
        for emh_type in self.emh_types:
            if emh_name in self.emh[emh_type]:
                return emh_type
        raise ExceptionCrue10("Le type de l'EMH %s n'est pas déterminable, "
                              "probablement car son nom est mal orthographié." % emh_name)

    def get_variable_position(self, emh_type, varname):
        try:
            return self.variables[emh_type].index(varname)
        except ValueError:
            raise ExceptionCrue10("La variable `%s` n'est pas disponible pour les %ss\n"
                                  "Les variables possibles sont : %s"
                                  % (varname, emh_type.lower(), self.variables[emh_type]))

    def get_emh_position(self, emh_type, emh_name):
        try:
            return self.emh[emh_type].index(emh_name)
        except ValueError:
            raise ExceptionCrue10("L'EMH `%s` n'est pas dans la liste des %s" % (emh_name, emh_type.lower()))

    def get_res_calc_pseudoperm(self, calc_name):
        """
        Obtenir les métadonnées des résultats du calcul pseudo-permanent demandé

        :param calc_name: nom du calcul
        :type calc_name: str
        :rtype: ResCalcPseudoPerm
        """
        try:
            return self.res_calc_pseudoperm[calc_name]
        except KeyError:
            if len(self.res_calc_pseudoperm) > 0:
                raise ExceptionCrue10("Calcul permanent `%s` non trouvé !\nLes noms de calculs possibles sont : %s."
                                      % (calc_name, ', '.join(self.res_calc_pseudoperm.keys())))
            else:
                raise ExceptionCrue10("Calcul permanent `%s` non trouvé !\nAucun calcul n'est trouvé." % calc_name)

    def get_res_calc_trans(self, calc_name):
        """
        Obtenir les métadonnées des résultats du calcul transitoire demandé

        :param calc_name: nom du calcul
        :type calc_name: str
        :rtype: ResCalcTrans
        """
        try:
            return self.res_calc_trans[calc_name]
        except KeyError:
            if len(self.res_calc_trans) > 0:
                raise ExceptionCrue10("Calcul transitoire `%s` non trouvé !\nLes noms de calculs possibles sont : %s."
                                      % (calc_name, ', '.join(self.res_calc_trans.keys())))
            else:
                raise ExceptionCrue10("Calcul transitoire `%s` non trouvé !\nAucun calcul n'est trouvé." % calc_name)

    def summary(self):
        text = ""
        for emh_type in self.emh_types:
            if len(self.emh[emh_type]) > 0 and len(self.variables[emh_type]) > 0:
                text += "~> %i %s (avec %i variables)\n" % (len(self.emh[emh_type]), emh_type,
                                                            len(self.variables[emh_type]))
        text += "=> %s calculs permanents et %i calculs transitoires\n" \
                % (len(self.res_calc_pseudoperm), len(self.res_calc_trans))
        return text

    def get_data_pseudoperm(self, calc_name):
        """
        Obtenir des tableaux numpy de résultats du calcul pseudo-permanent demandé pour chaque type d'EMH.
        Les tableaux ont 2 dimensions : temps, emh, variable.

        :param calc_name: nom du calcul
        :type calc_name: str
        :rtype: dict(np.ndarray)
        """
        calc = self.get_res_calc_pseudoperm(calc_name)
        return calc.file_pos.get_data(self._res_pattern, True, self._emh_type_first_branche)

    def get_data_all_pseudoperm(self):
        """
        Obtenir des tableaux numpy de résultats de tous les calculs pseudo-permanent demandé pour chaque type d'EMH.
        Les tableaux ont 3 dimensions : calcul, emh, variable.

        :rtype: dict(np.ndarray)
        """
        data = {}
        for idx_calc, calc_name in enumerate(self.res_calc_pseudoperm.keys()):
            res = self.get_data_pseudoperm(calc_name)
            if not data:
                for emh_type, values in res.items():
                    data[emh_type] = np.empty((len(self.res_calc_pseudoperm), values.shape[0], values.shape[1]))
            for emh_type, values in res.items():
                data[emh_type][idx_calc, :, :] = values
        return data

    def extract_profil_long_pseudoperm_as_dataframe(self, calc_name, branches, var_names=None):
        """
        Extraction d'un profil en long (le long de branches) d'un calcul pseudo-permanent

        :param calc_name: nom du calcul pseudo-permanent
        :type calc_name: str
        :param branches: liste des branches
        :type branches: list(str)
        :param var_names: liste des variables (si absent alors tout est exporté)
        :type var_names: list
        :return: tableau de valeurs du profil en long
        :rtype: pd.DataFrame
        """
        res_perm = self.get_data_pseudoperm(calc_name)['Section']

        if var_names is None:
            var_names = self.variables['Section']

        branche_names = []
        section_names = []
        distances_list = []
        distance = 0.0
        for branche in branches:
            for i, section in enumerate(branche.liste_sections_dans_branche):
                branche_names.append(branche.id)
                section_names.append(section.id)
                distances_list.append(distance + section.xp)
                if i == len(branche.liste_sections_dans_branche) - 1:
                    distance += section.xp

        pos_sections = [self.emh['Section'].index(section_name) for section_name in section_names]
        pos_variables = [self.variables['Section'].index(var) for var in var_names]
        array = res_perm[pos_sections, :][:, pos_variables]

        values_in_dict = OrderedDict([('branche', branche_names), ('section', section_names),
                                      ('distance', distances_list)])
        for i, var in enumerate(var_names):
            values_in_dict[var] = array[:, i]
        return pd.DataFrame(values_in_dict)

    def extract_profil_long_trans_at_time_as_dataframe(self, calc_name, branches, idx_time, var_names=None):
        """
        Extraction d'un profil en long (le long de branches) d'un calcul transitoire à un enregistrement temporel donné

        :param calc_name: nom du calcul transitoire
        :type calc_name: str
        :param branches: liste des branches
        :type branches: list(str)
        :param idx_time: index de l'enregistrement temporel (0-indexed)
        :type idx_time: int
        :param var_names: liste des variables (si absent alors tout est exporté)
        :type var_names: list
        :return: tableau de valeurs du profil en long
        :rtype: pd.DataFrame
        """
        res = self.get_data_trans(calc_name)['Section']
        res_trans = res[idx_time, :, :]

        if var_names is None:
            var_names = self.variables['Section']

        branche_names = []
        section_names = []
        distances_list = []
        distance = 0.0
        for branche in branches:
            for i, section in enumerate(branche.liste_sections_dans_branche):
                branche_names.append(branche.id)
                section_names.append(section.id)
                distances_list.append(distance + section.xp)
                if i == len(branche.liste_sections_dans_branche) - 1:
                    distance += section.xp

        pos_sections = [self.emh['Section'].index(section_name) for section_name in section_names]
        pos_variables = [self.variables['Section'].index(var) for var in var_names]
        array = res_trans[pos_sections, :][:, pos_variables]

        values_in_dict = OrderedDict([('branche', branche_names), ('section', section_names),
                                      ('distance', distances_list)])
        for i, var in enumerate(var_names):
            values_in_dict[var] = array[:, i]
        return pd.DataFrame(values_in_dict)

    def extract_profil_long_trans_max_as_dataframe(self, calc_name, branches, var_names=None,
                                                   start_time=-float('inf'), end_time=float('inf')):
        """
        Extraction d'un profil en long (le long de branches) des maximums d'un calcul transitoire

        :param calc_name: nom du calcul transitoire
        :type calc_name: str
        :param branches: liste des branches
        :type branches: list(Branche)
        :param var_names: liste des variables (si absent alors tout est exporté)
        :type var_names: list
        :param start_time: borne inférieure temporelle (début du transitoire si absent)
        :type start_time: float
        :param end_time: borne supérieure temporelle (fin du transitoire si absent)
        :type end_time: float
        :return: tableau de valeurs du profil en long
        :rtype: pd.DataFrame
        """
        time = self.get_res_calc_trans(calc_name).time_serie()
        res = self.get_data_trans(calc_name)['Section']
        res_trans = np.max(res[np.logical_and(start_time <= time, time <= end_time), :, :], axis=0)

        if var_names is None:
            var_names = self.variables['Section']

        branche_names = []
        section_names = []
        distances_list = []
        distance = 0.0
        for branche in branches:
            for i, section in enumerate(branche.liste_sections_dans_branche):
                branche_names.append(branche.id)
                section_names.append(section.id)
                distances_list.append(distance + section.xp)
                if i == len(branche.liste_sections_dans_branche) - 1:
                    distance += section.xp

        pos_sections = [self.emh['Section'].index(section_name) for section_name in section_names]
        pos_variables = [self.variables['Section'].index(var) for var in var_names]
        array = res_trans[pos_sections, :][:, pos_variables]

        values_in_dict = OrderedDict([('branche', branche_names), ('section', section_names),
                                      ('distance', distances_list)])
        for i, var in enumerate(var_names):
            values_in_dict[var] = array[:, i]
        return pd.DataFrame(values_in_dict)

    def get_data_trans(self, calc_name):
        """
        Obtenir des tableaux numpy de résultats du calcul transitoire demandé pour chaque type d'EMH.
        Les tableaux ont 3 dimensions : temps, emh, variable.

        :param calc_name: nom du calcul
        :return: dict(np.ndarray)
        """
        calc = self.get_res_calc_trans(calc_name)

        # Append arrays
        res_all = {}
        for i, (time_sec, file_pos) in enumerate(calc.frame_list):
            res = file_pos.get_data(self._res_pattern, False, self._emh_type_first_branche)
            for emh_type in self.emh_types:
                if i == 0:
                    res_all[emh_type] = []
                res_all[emh_type].append(res[emh_type])

        # Stack arrays
        for emh_type in self.emh_types:
            res_all[emh_type] = np.array(res_all[emh_type])
        return res_all

    def get_all_pseudoperm_var_at_emhs_as_array(self, varname, emh_list):
        """
        Obtenir un tableau numpy avec les valeurs numériques de la variable demandée aux EMHs pour tous les calculs
        pseudo-permnants

        :param varname: nom de la variable à extraire
        :type varname: str
        :param emh_list: liste des EMHs concernées
        :type emh_list: list(str)
        :return: tableau numpy (lignes = calculs pseudo-permanents, colonnes = EMHs)
        :rtype: np.ndarray
        """
        values = np.empty((len(self.res_calc_pseudoperm), len(emh_list)))

        emh_types = []
        for emh_name in emh_list:
            emh_types.append(self.emh_type(emh_name))

        for i, calc_name in enumerate(self.res_calc_pseudoperm.keys()):
            res = self.get_data_pseudoperm(calc_name)
            for j, (emh_name, emh_type) in enumerate(zip(emh_list, emh_types)):
                emh_pos = self.get_emh_position(emh_type, emh_name)
                var_pos = self.get_variable_position(emh_type, varname)
                values[i, j] = res[emh_type][emh_pos, var_pos]
        return values

    def get_trans_var_at_emhs_as_array(self, calc_name, varname, emh_list):
        """
        Obtenir un tableau numpy avec les valeurs numériques de la variable demandée aux EMHs pour l'ensemble des
        temps du calcul transitoire demandé

        :param calc_name: nom du calcul transitoire
        :type calc_name: str
        :param varname: nom de la variable à extraire
        :type varname: str
        :param emh_list: liste des EMHs concernées
        :type emh_list: list(str)
        :return: tableau numpy (lignes = temps du calcul transitoire, colonnes = EMHs)
        :rtype: np.ndarray
        """
        calc = self.get_res_calc_trans(calc_name)
        values = np.empty((len(calc.frame_list), len(emh_list)))

        emh_types = []
        for emh_name in emh_list:
            emh_types.append(self.emh_type(emh_name))

        res = self.get_data_trans(calc_name)
        for i, (emh_name, emh_type) in enumerate(zip(emh_list, emh_types)):
            emh_pos = self.get_emh_position(emh_type, emh_name)
            var_pos = self.get_variable_position(emh_type, varname)
            values[:, i] = res[emh_type][:, emh_pos, var_pos]
        return values

    def extract_res_trans_as_dataframe(self, lst_var, lst_emh):
        """
        Exports as DataFrame tabular results: time, val1, val2, etc. where each vali stands for a varname for an EMH.

        :param lst_var: liste des noms de variables à extraire
        :type lst_var: list(str)
        :param lst_emh: liste des EMH concernés
        :type lst_emh: list(str)
        :return: DataFrame avec le tableau des résultats, un pas de temps par ligne.
        :rtype: pd.DataFrame
        """
        # Parcours des calculs
        for cal_name in self.res_calc_trans.keys():
            # Préparation des dictionnaires de listes
            dic_res = {}  # Dictionnaire des résultats, sous forme d'un dictionnaire de listes ayant chacune la dimension du nombre de pdt (pas de temps)
            lst_time = self.get_res_calc_trans(cal_name).time_serie()
            lst_calc = []
            for i in range(len(lst_time)):
                lst_calc.append(cal_name)
            dic_res['Calcul'] = lst_calc  # La première colonne est le nom du calcul
            dic_res['Temps'] = lst_time  # La deuxième colonne est le pdt dans le calcul
            for emh_name in lst_emh:
                for var_name in lst_var:
                    try:
                        # Les colonnes suivantes sont les valeurs pour chaque nom de variable et nom d'EMH (exemple 'Z St_P146.0a')
                        lst_emh_name = []
                        lst_emh_name.append(emh_name)  # On a besoin d'une liste de noms d'EHM avec un seul élément
                        lst_res = self.get_trans_var_at_emhs_as_array(cal_name, var_name, lst_emh_name)  # Récupération d'une liste de listes (chacune à un seul élément)
                        lst_res_1d = []
                        for itm_res in lst_res:
                            lst_res_1d.append(itm_res[0])  # Chaque ligne de la liste est elle-même une liste à un élément, on le récupère
                        if len(lst_res_1d) > 0:
                            dic_res[var_name + " " + emh_name] = lst_res_1d  # L'entrée du dictionnaire (exemple 'Z St_P146.0a') contient la liste des valeurs pour chaque pdt
                    except ExceptionCrue10:
                        # A priori, incompatibilité entre nom de variable et type d'EHM: pas grave, on ne sort juste pas ces résultats
                        pass

            # Le DataFrame en retour est construit à partir d'un dictionnaire de listes
            return pd.DataFrame(dic_res)  # DataFrame (=tableau de valeurs structuré, Pandas)

    def write_all_calc_pseudoperm_in_csv(self, csv_path):
        """
        Écrire un fichier CSV avec les résultats de tous les calculs pseudo-permanents
        L'en-tête est : "calc;time;emh_type;emh;variable;value"

        :param csv_path: chemin vers le fichier CSV
        :type csv_path: str
        """
        if version_info[0] == 3:   # Python2 fix
            arguments = {'mode': 'w', 'newline': ''}
        else:
            arguments = {'mode': 'wb'}
        with open(csv_path, **arguments) as csv_file:
            fieldnames = ['calc', 'time', 'emh_type', 'emh', 'variable', 'value']
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
            csv_writer.writeheader()
            for i_calc, calc_name in enumerate(self.res_calc_pseudoperm.keys()):
                res = self.get_data_pseudoperm(calc_name)
                for emh_type in self.emh_types:
                    variables = self.variables[emh_type]
                    for emh_name, row in zip(self.emh[emh_type], res[emh_type]):
                        for variable, value in zip(variables, row):
                            csv_writer.writerow({'calc': calc_name,
                                                 'time': i_calc + 1,
                                                 'emh_type': emh_type,
                                                 'emh': emh_name,
                                                 'variable': variable,
                                                 'value': FMT_FLOAT_CSV % value})

    def write_all_calc_trans_in_csv(self, csv_path):
        """
        Écrire un fichier CSV avec les résultats de tous les calculs transitoires
        L'en-tête est : "calc;time;emh_type;emh;variable;value"

        :param csv_path: chemin vers le fichier CSV
        :type csv_path: str
        """
        if version_info[0] == 3:   # Python2 fix
            arguments = {'mode': 'w', 'newline': ''}
        else:
            arguments = {'mode': 'wb'}
        with open(csv_path, **arguments) as csv_file:
            fieldnames = ['calc', 'time', 'emh_type', 'emh', 'variable', 'value']
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
            csv_writer.writeheader()
            for calc_name in self.res_calc_trans.keys():
                res = self.get_data_trans(calc_name)
                for emh_type in self.emh_types:
                    variables = self.variables[emh_type]
                    for time_sec, res_frame in zip(self.get_res_calc_trans(calc_name).time_serie(), res[emh_type]):
                        for emh_name, row in zip(self.emh[emh_type], res_frame):
                            for variable, value in zip(variables, row):
                                csv_writer.writerow({'calc': calc_name,
                                                     'time': time_sec,
                                                     'emh_type': emh_type,
                                                     'emh': emh_name,
                                                     'variable': variable,
                                                     'value': FMT_FLOAT_CSV % value})

    def __repr__(self):
        return "Résultats run #%s (%i permanents, %i transitoires)" % (self.run_id, len(self.res_calc_pseudoperm),
                                                                       len(self.res_calc_trans))
