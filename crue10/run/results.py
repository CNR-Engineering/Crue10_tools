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
from crue10.utils.settings import CSV_DELIMITER


FMT_FLOAT_CSV = '{:.6e}'

TIME_REGEX = re.compile(r'P(?P<days>[0-9]+)DT(?P<hours>[0-9]+)H(?P<mins>[0-9]+)M(?P<secs>[0-9]+)S')


def get_time_in_seconds(time_str):
    match = TIME_REGEX.match(time_str)
    values = {duration: int(counter) for duration, counter in match.groupdict().items()}
    return ((values['days'] * 24 + values['hours']) * 60 + values['mins']) * 60 + values['secs']


class FilePosition:
    """
    Binary file is in little endian with only 8-bytes values (ie. double precision for numeric values)
    """
    ENCODING = 'utf-8'
    FLOAT_SIZE = 8
    FLOAT_TYPE = 'd'

    def __init__(self, rbin_path, byte_offset):
        self.rbin_path = rbin_path
        self.byte_offset = byte_offset

    def get_data(self, res_pattern, is_steady, emh_type_first_branche):
        res = {}
        with io.open(self.rbin_path, 'rb') as resin:
            resin.seek(self.byte_offset * FilePosition.FLOAT_SIZE)

            # Check calculation type
            calc_delimiter = resin.read(FilePosition.FLOAT_SIZE).decode(FilePosition.ENCODING).strip()
            if is_steady:
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


class CalcPseudoPerm:
    """Metadata for a steady calculation"""

    def __init__(self, name, bin_path, byte_offset):
        self.name = name
        self.file_pos = FilePosition(bin_path, byte_offset)

    def __repr__(self):
        return "Calcul permanent #%s" % self.name


class CalcTrans:
    """Metadata for an unsteady calculation"""

    def __init__(self, name):
        self.name = name
        self.frame_list = []

    def add_frame(self, time_sec, bin_path, byte_offset):
        self.frame_list.append((time_sec, FilePosition(bin_path, byte_offset)))

    def time_serie(self):
        return np.array([frame[0] for frame in self.frame_list])

    def __repr__(self):
        return "Calcul non permanent #%s (%i temps)" % (self.name, len(self.frame_list))


class RunResults:
    """
    Results data for a single Run
    - rcal_root <ET..Element>: rcal XML element
    - rcal_path <str>: path to rcal file
    - rcal_folder <str>: folder path to rcal file
    - self.emh_types <list>: list of "secondary" EMH types
        for example: ['Noeud', 'Casier', 'Section', 'BrancheBarrageFilEau', 'BrancheOrifice', 'BrancheSaintVenant'...]
    - emh <OrderedDict>: dictionary with secondary types as keys giving a list of EMH names
    - variables <OrderedDict>: dictionary with secondary types as keys giving a list of variable identifiers
    - calc_steady_dict <OrderedDict>: dictionary with steady calculations
    - calc_unsteady_dict <OrderedDict>: dictionary with unsteady calculations

    - _emh_type_first_branche <str>: first EMH secondary type for Branche (e.g. 'BrancheBarrageFilEau')
    - _res_pattern <list>: list with a tuple (emh_type, shape)
    """
    EMH_PRIMARY_TYPES = ['Noeud', 'Casier', 'Section', 'Branche']

    def __init__(self, rcal_path):
        self.rcal_root = ET.parse(rcal_path).getroot()
        self.rcal_path = rcal_path
        self.rcal_folder = os.path.dirname(rcal_path)
        self.emh_types = []
        self.emh = OrderedDict()
        self.variables = OrderedDict()
        self.calc_steady_dict = OrderedDict()
        self.calc_unsteady_dict = OrderedDict()

        self._emh_type_first_branche = None
        self._res_pattern = []

        self._read_parametrage()
        self._read_structure()
        self._read_rescalc()
        self._set_res_pattern()

    @property
    def run_id(self):
        return os.path.basename(os.path.normpath(os.path.join(self.rcal_folder, '..')))

    def _add_variables_names(self, elt, emh_sec):
        if emh_sec not in self.variables:
            self.variables[emh_sec] = []
        for sub_elt in elt:
            if sub_elt.tag.endswith('VariableRes'):
                self.variables[emh_sec].append(sub_elt.get('NomRef'))

    def _add_emh_names(self, elt, emh_sec):
        if int(elt.get('NbrMot')) > 0:  # Avoid empty lists in self.emh
            if emh_sec not in self.emh:
                if emh_sec.startswith('Branche') and self._emh_type_first_branche is None:
                    self._emh_type_first_branche = emh_sec
                self.emh_types.append(emh_sec)
                self.emh[emh_sec] = []
            for sub_elt in elt:
                if not sub_elt.tag.endswith('VariableRes'):
                    emh_name = sub_elt.get('NomRef')
                    self.emh[emh_sec].append(emh_name)

    def _read_parametrage(self):
        nb_bytes = int(self.rcal_root.find(PREFIX + 'Parametrage').find(PREFIX + 'NbrOctetMot').text)
        if nb_bytes != FilePosition.FLOAT_SIZE:
            raise ExceptionCrue10("La taille des données (%i octets) n'est pas supportée" % nb_bytes)

    def _read_structure(self):
        """
        EMH are read from following xpaths :
        - Noeuds/NoeudNiveauContinu/Noeud
        - Casiers/CasierProfil/Casier
        - Sections/{SectionIdem,SectionInterpolee,SectionProfil,SectionSansGeometrie}/Section (mêmes variables)
        - Branches/Branche*/Branche
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
                if emh_type == 'Noeud':
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
            calc_steady = CalcPseudoPerm(calc.get('NomRef'), os.path.join(self.rcal_folder, calc.get('Href')),
                                         int(calc.get('OffsetMot')))
            self.calc_steady_dict[calc_steady.name] = calc_steady

        for calc in self.rcal_root.find(PREFIX + 'ResCalcTranss'):
            calc_unsteady = CalcTrans(calc.get('NomRef'))
            for pdt in calc:
                calc_unsteady.add_frame(get_time_in_seconds(pdt.get('TempsSimu')),
                                        os.path.join(self.rcal_folder, pdt.get('Href')), int(pdt.get('OffsetMot')))
            self.calc_unsteady_dict[calc_unsteady.name] = calc_unsteady

    def _set_res_pattern(self):
        emh_types_with_res = []
        for emh_type in self.emh_types:
            emh_types_with_res.append(emh_type)
            self._res_pattern.append((emh_type, (len(self.emh[emh_type]), len(self.variables[emh_type]))))
        # Add emh_types which have no result data (because delimiter is still present)
        for i, emh_type in enumerate(RunResults.EMH_PRIMARY_TYPES[:-1]):
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

    def get_calc_steady(self, calc_name):
        try:
            return self.calc_steady_dict[calc_name]
        except KeyError:
            if len(self.calc_steady_dict) > 0:
                raise ExceptionCrue10("Calcul permanent `%s` non trouvé !\nLes noms de calculs possibles sont : %s."
                                      % (calc_name, ', '.join(self.calc_steady_dict.keys())))
            else:
                raise ExceptionCrue10("Calcul permanent `%s` non trouvé !\nAucun calcul n'est trouvé." % calc_name)

    def get_calc_unsteady(self, calc_name):
        try:
            return self.calc_unsteady_dict[calc_name]
        except KeyError:
            if len(self.calc_unsteady_dict) > 0:
                raise ExceptionCrue10("Calcul transitoire `%s` non trouvé !\nLes noms de calculs possibles sont : %s."
                                      % (calc_name, ', '.join(self.calc_unsteady_dict.keys())))
            else:
                raise ExceptionCrue10("Calcul transitoire `%s` non trouvé !\nAucun calcul n'est trouvé." % calc_name)

    def summary(self):
        text = ""
        for emh_type in self.emh_types:
            if len(self.emh[emh_type]) > 0 and len(self.variables[emh_type]) > 0:
                text += "~> %i %s (avec %i variables)\n" % (len(self.emh[emh_type]), emh_type,
                                                            len(self.variables[emh_type]))
        text += "=> %s calculs permanents et %i calculs transitoires\n" % (len(self.calc_steady_dict), len(self.calc_unsteady_dict))
        return text

    def get_res_steady(self, calc_name):
        calc = self.get_calc_steady(calc_name)
        return calc.file_pos.get_data(self._res_pattern, True, self._emh_type_first_branche)

    def get_res_steady_at_sections_along_branches_as_dataframe(self, calc_name, branches, var_names=None):
        calc = self.get_calc_steady(calc_name)
        res_perm = calc.file_pos.get_data(self._res_pattern, True, self._emh_type_first_branche)['Section']

        if var_names is None:
            var_names = self.variables['Section']

        branche_names = []
        section_names = []
        distances_list = []
        distance = 0.0
        for branche in branches:
            for section in branche.liste_sections_dans_branche:
                distance += section.xp
                branche_names.append(branche.id)
                section_names.append(section.id)
                distances_list.append(distance)

        pos_sections = [self.emh['Section'].index(section_name) for section_name in section_names]
        pos_variables = [self.variables['Section'].index(var) for var in var_names]
        array = res_perm[pos_sections, :][:, pos_variables]

        values_in_dict = {'branche': branche_names, 'section': section_names, 'distance': distances_list}
        values_in_dict.update({var: array[:, i] for i, var in enumerate(var_names)})
        return pd.DataFrame(values_in_dict)

    def get_res_unsteady(self, calc_name):
        calc = self.get_calc_unsteady(calc_name)

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

    def get_res_all_steady_var_at_emhs(self, varname, emh_list):
        values = np.empty((len(self.calc_steady_dict), len(emh_list)))

        emh_types = []
        for emh_name in emh_list:
            emh_types.append(self.emh_type(emh_name))

        for i, calc_name in enumerate(self.calc_steady_dict.keys()):
            res = self.get_res_steady(calc_name)
            for j, (emh_name, emh_type) in enumerate(zip(emh_list, emh_types)):
                emh_pos = self.get_emh_position(emh_type, emh_name)
                var_pos = self.get_variable_position(emh_type, varname)
                values[i, j] = res[emh_type][emh_pos, var_pos]
        return values

    def get_res_unsteady_var_at_emhs(self, calc_name, varname, emh_list):
        calc = self.get_calc_unsteady(calc_name)
        values = np.empty((len(calc.frame_list), len(emh_list)))

        emh_types = []
        for emh_name in emh_list:
            emh_types.append(self.emh_type(emh_name))

        res = self.get_res_unsteady(calc_name)
        for i, (emh_name, emh_type) in enumerate(zip(emh_list, emh_types)):
            emh_pos = self.get_emh_position(emh_type, emh_name)
            var_pos = self.get_variable_position(emh_type, varname)
            values[:, i] = res[emh_type][:, emh_pos, var_pos]
        return values

    def export_calc_steady_as_csv(self, csv_path):
        """
        Write CSV containing all `CalcPseudoPerm` results
        Header is: "calc;emh_type;emh;variable;value"
        """
        if version_info[0] == 3:   # Python2 fix: do not add `newline` argument
            arguments = {'newline': ''}
        else:
            arguments = {}
        with open(csv_path, 'w', **arguments) as csv_file:  # Python2.7 fix: io.open is not compatible with csv
            fieldnames = ['calc', 'emh_type', 'emh', 'variable', 'value']
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
            csv_writer.writeheader()
            for calc_name in self.calc_steady_dict.keys():
                res = self.get_res_steady(calc_name)
                for emh_type in self.emh_types:
                    variables = self.variables[emh_type]
                    for emh_name, row in zip(self.emh[emh_type], res[emh_type]):
                        for variable, value in zip(variables, row):
                            csv_writer.writerow({'calc': calc_name,
                                                 'emh_type': emh_type,
                                                 'emh': emh_name,
                                                 'variable': variable,
                                                 'value': FMT_FLOAT_CSV.format(value)})

    def export_calc_unsteady_as_csv(self, csv_path):
        """
        Write CSV containing all `CalcTrans` results
        Header is: "calc;time;emh_type;emh;variable;value"
        """
        if version_info[0] == 3:   # Python2 fix: do not add `newline` argument
            arguments = {'newline': ''}
        else:
            arguments = {}
        with open(csv_path, 'w', **arguments) as csv_file:  # Python2.7 fix: io.open is not compatible with csv
            fieldnames = ['calc', 'time', 'emh_type', 'emh', 'variable', 'value']
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=CSV_DELIMITER)
            csv_writer.writeheader()
            for calc_name in self.calc_unsteady_dict.keys():
                res = self.get_res_unsteady(calc_name)
                for emh_type in self.emh_types:
                    variables = self.variables[emh_type]
                    for time_sec, res_frame in zip(self.calc_unsteady_dict[calc_name].time_serie(), res[emh_type]):
                        for emh_name, row in zip(self.emh[emh_type], res_frame):
                            for variable, value in zip(variables, row):
                                csv_writer.writerow({'calc': calc_name,
                                                     'time': time_sec,
                                                     'emh_type': emh_type,
                                                     'emh': emh_name,
                                                     'variable': variable,
                                                     'value': FMT_FLOAT_CSV.format(value)})

    def __repr__(self):
        return "Résultats run #%s (%i permanents, %i transitoires)" % (self.run_id, len(self.calc_steady_dict),
                                                                       len(self.calc_unsteady_dict))
