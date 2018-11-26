import numpy as np
import re
import struct

from crue10.utils import CrueError


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

    def __init__(self, bin_path, byte_offset):
        self.bin_path = bin_path
        self.byte_offset = byte_offset

    def get_data(self, res_pattern, is_steady, emh_type_first_branche):
        res = {}
        with open(self.bin_path, 'rb') as resin:
            resin.seek(self.byte_offset * FilePosition.FLOAT_SIZE)

            # Check calculation type
            calc_delimiter = resin.read(FilePosition.FLOAT_SIZE).decode(FilePosition.ENCODING).strip()
            if is_steady:
                if calc_delimiter != 'RcalPp':
                    raise CrueError("Le calcul n'est pas permanent !")
            else:
                if calc_delimiter != 'RcalPdt':
                    raise CrueError("Le calcul n'est pas transitoire !")

            for emh_type, (nb_emh, nb_var) in res_pattern:
                if not emh_type.startswith('Branche') or emh_type == emh_type_first_branche:
                    emh_delimiter = resin.read(FilePosition.FLOAT_SIZE).decode(FilePosition.ENCODING).strip()
                    if emh_delimiter not in emh_type:
                        raise CrueError("Les EMH attendus sont %s (au lieu de %s)" % (emh_type, emh_delimiter))
                values = struct.unpack('<' + str(nb_emh * nb_var) + FilePosition.FLOAT_TYPE,
                                       resin.read(nb_emh * nb_var * FilePosition.FLOAT_SIZE))
                res[emh_type] = np.array(values).reshape((nb_emh, nb_var))
        return res


class CalculPermanent:
    def __init__(self, name, bin_path, byte_offset):
        self.name = name
        self.file_pos = FilePosition(bin_path, byte_offset)

    def __repr__(self):
        return "CalculPermanent #%s" % self.name


class CalculTransitoire:
    def __init__(self, name):
        self.name = name
        self.frame_list = []

    def add_frame(self, time_sec, bin_path, byte_offset):
        self.frame_list.append((time_sec, FilePosition(bin_path, byte_offset)))

    def time_serie(self):
        return [frame[0] for frame in self.frame_list]

    def __repr__(self):
        return "CalculTransitoire #%s (%i frames)" % (self.name, len(self.frame_list))
