from collections import OrderedDict
import csv
import numpy as np
import os.path
import xml.etree.ElementTree as ET

from crue10.utils import CrueError, PREFIX

from .calculs import CalculPermanent, CalculTransitoire, FilePosition, get_time_in_seconds


FMT_FLOAT_CSV = '{:.6e}'


class CrueRun:
    EMH_PRIMARY_TYPES = ['Noeud', 'Casier', 'Section', 'Branche']

    def __init__(self, rcal_path):
        self.rcal = ET.parse(rcal_path).getroot()
        self.rcal_folder = os.path.dirname(rcal_path)
        self.emh_types = []
        self.emh_type_first_branche = None
        self.emh = OrderedDict()
        self.variables = OrderedDict()
        self.calc_perms = {}
        self.calc_trans = {}
        self.res_pattern = []

        self._read_parametrage()
        self._read_structure()
        self._read_rescalc()
        self.set_res_pattern()

    def _add_variables_names(self, elt, emh_sec):
        if emh_sec not in self.variables:
            self.variables[emh_sec] = []
        for sub_elt in elt:
            if sub_elt.tag.endswith('VariableRes'):
                self.variables[emh_sec].append(sub_elt.get('NomRef'))

    def _add_emh_names(self, elt, emh_sec):
        if int(elt.get('NbrMot')) > 0:  # Avoid empty lists in self.emh
            if emh_sec not in self.emh:
                if emh_sec.startswith('Branche') and self.emh_type_first_branche is None:
                    self.emh_type_first_branche = emh_sec
                self.emh_types.append(emh_sec)
                self.emh[emh_sec] = []
            for sub_elt in elt:
                if not sub_elt.tag.endswith('VariableRes'):
                    emh_name = sub_elt.get('NomRef')
                    if emh_name.startswith('Ca_'):
                        # Replace `Ca_` prefix by `Cd_`
                        emh_name = 'Cd_' + emh_name[3:]
                    self.emh[emh_sec].append(emh_name)

    def _read_parametrage(self):
        nb_bytes = int(self.rcal.find(PREFIX + 'Parametrage').find(PREFIX + 'NbrOctetMot').text)
        if nb_bytes != FilePosition.FLOAT_SIZE:
            raise CrueError("La taille des données (%i octets) n'est pas supportée" % nb_bytes)

    def _read_structure(self):
        """
        EMH are read from following xpaths :
        - Noeuds/NoeudNiveauContinu/Noeud
        - Casiers/CasierProfil/Casier
        - Sections/{SectionIdem,SectionInterpolee,SectionProfil,SectionSansGeometrie}/Section (mêmes variables)
        - Branches/Branche*/Branche
        """
        for emh_list in self.rcal.find(PREFIX + 'StructureResultat'):
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
        for calc in self.rcal.find(PREFIX + 'ResCalcPerms'):
            calc_perm = CalculPermanent(calc.get('NomRef'), os.path.join(self.rcal_folder, calc.get('Href')),
                                        int(calc.get('OffsetMot')))
            self.calc_perms[calc_perm.name] = calc_perm

        for calc in self.rcal.find(PREFIX + 'ResCalcTranss'):
            calc_trans = CalculTransitoire(calc.get('NomRef'))
            for pdt in calc:
                calc_trans.add_frame(get_time_in_seconds(pdt.get('TempsSimu')),
                                     os.path.join(self.rcal_folder, pdt.get('Href')), int(pdt.get('OffsetMot')))
            self.calc_trans[calc_trans.name] = calc_trans

    def set_res_pattern(self):
        for emh_type in self.emh_types:
            self.res_pattern.append((emh_type, (len(self.emh[emh_type]), len(self.variables[emh_type]))))

    def emh_type(self, emh_name):
        for emh_type in self.emh_types:
            if emh_name in self.emh[emh_type]:
                return emh_type
        raise CrueError("Le type de l'EMH %s n'est pas déterminable" % emh_name)

    def get_variable_position(self, emh_type, varname):
        try:
            return self.variables[emh_type].index(varname)
        except ValueError:
            raise CrueError("La variable `%s` n'est pas disponible pour les %s" % (varname, emh_type.lower()))

    def get_emh_position(self, emh_type, emh_name):
        try:
            return self.emh[emh_type].index(emh_name)
        except ValueError:
            raise CrueError("L'EMH `%s` n'est pas dans la liste des %s" % (emh_name, emh_type.lower()))

    def get_calc_perm(self, calc_name):
        try:
            return self.calc_perms[calc_name]
        except KeyError:
            if len(self.calc_perms) > 0:
                raise CrueError("Calcul permanent `%s` non trouvé !\nLes noms de calculs possibles sont : %s."
                                % (calc_name, ', '.join(self.calc_perms.keys())))
            else:
                raise CrueError("Calcul permanent `%s` non trouvé !\nAucun calcul n'est trouvé." % calc_name)

    def get_calc_trans(self, calc_name):
        try:
            return self.calc_trans[calc_name]
        except KeyError:
            if len(self.calc_trans) > 0:
                raise CrueError("Calcul transitoire `%s` non trouvé !\nLes noms de calculs possibles sont : %s."
                                % (calc_name, ', '.join(self.calc_trans.keys())))
            else:
                raise CrueError("Calcul transitoire `%s` non trouvé !\nAucun calcul n'est trouvé." % calc_name)

    def summary(self):
        text = ""
        for emh_type in self.emh_types:
            if len(self.emh[emh_type]) > 0 and len(self.variables[emh_type]) > 0:
                text += "~> %i %s (avec %i variables)\n" % (len(self.emh[emh_type]), emh_type,
                                                            len(self.variables[emh_type]))
        text += "=> %s calculs permanents et %i calculs transitoires\n" % (len(self.calc_perms), len(self.calc_trans))
        return text

    def get_res_perm(self, calc_name):
        calc = self.get_calc_perm(calc_name)
        return calc.file_pos.get_data(self.res_pattern, True, self.emh_type_first_branche)

    def get_res_trans(self, calc_name):
        calc = self.get_calc_trans(calc_name)

        # Append arrays
        res_all = {}
        for i, (time_sec, file_pos) in enumerate(calc.frame_list):
            res = file_pos.get_data(self.res_pattern, False, self.emh_type_first_branche)
            for emh_type in self.emh_types:
                if i == 0:
                    res_all[emh_type] = []
                res_all[emh_type].append(res[emh_type])

        # Stack arrays
        for emh_type in self.emh_types:
            res_all[emh_type] = np.stack(res_all[emh_type], axis=0)
        return res_all

    def get_res_all_perm_var_at_emhs(self, varname, emh_list):
        values = np.empty((len(self.calc_perms), len(emh_list)))

        emh_types = []
        for emh_name in emh_list:
            emh_types.append(self.emh_type(emh_name))

        for i, calc_name in enumerate(self.calc_perms.keys()):
            res = self.get_res_perm(calc_name)
            for j, (emh_name, emh_type) in enumerate(zip(emh_list, emh_types)):
                emh_pos = self.get_emh_position(emh_type, emh_name)
                var_pos = self.get_variable_position(emh_type, varname)
                values[i, j] = res[emh_type][emh_pos, var_pos]
        return values

    def get_res_trans_var_at_emhs(self, calc_name, varname, emh_list):
        calc = self.get_calc_trans(calc_name)
        values = np.empty((len(calc.frame_list), len(emh_list)))

        emh_types = []
        for emh_name in emh_list:
            emh_types.append(self.emh_type(emh_name))

        res = self.get_res_trans(calc_name)
        for i, (emh_name, emh_type) in enumerate(zip(emh_list, emh_types)):
            emh_pos = self.get_emh_position(emh_type, emh_name)
            var_pos = self.get_variable_position(emh_type, varname)
            values[:, i] = res[emh_type][:, emh_pos, var_pos]
        return values

    def export_calc_perm_as_csv(self, csv_path):
        """
        Write CSV containing all `CalculPermanent` results
        Header is calc;emh_type;emh;variable;value
        """
        with open(csv_path, 'w', newline='') as csv_file:
            fieldnames = ['calc', 'emh_type', 'emh', 'variable', 'value']
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=';')
            csv_writer.writeheader()
            for calc_name in self.calc_perms.keys():
                res = self.get_res_perm(calc_name)
                for emh_type in self.emh_types:
                    variables = self.variables[emh_type]
                    for emh_name, row in zip(self.emh[emh_type], res[emh_type]):
                        for variable, value in zip(variables, row):
                            csv_writer.writerow({'calc': calc_name,
                                                 'emh_type': emh_type,
                                                 'emh': emh_name,
                                                 'variable': variable,
                                                 'value': FMT_FLOAT_CSV.format(value)})

    def export_calc_trans_as_csv(self, csv_path):
        """
        Write CSV containing all `CalculTransitoire` results
        Header is calc;time;emh_type;emh;variable;value
        """
        with open(csv_path, 'w', newline='') as csv_file:
            fieldnames = ['calc', 'time', 'emh_type', 'emh', 'variable', 'value']
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=';')
            csv_writer.writeheader()
            for calc_name in self.calc_trans.keys():
                res = self.get_res_trans(calc_name)
                for emh_type in self.emh_types:
                    variables = self.variables[emh_type]
                    for time_sec, res_frame in zip(self.calc_trans[calc_name].time_serie(), res[emh_type]):
                        for emh_name, row in zip(self.emh[emh_type], res_frame):
                            for variable, value in zip(variables, row):
                                csv_writer.writerow({'calc': calc_name,
                                                     'time': time_sec,
                                                     'emh_type': emh_type,
                                                     'emh': emh_name,
                                                     'variable': variable,
                                                     'value': FMT_FLOAT_CSV.format(value)})
