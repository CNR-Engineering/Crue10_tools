# coding: utf-8
from crue10.utils import ExceptionCrue10


MO_FONTSIZE = 40

SM_FONTSIZE = 30

EMH_FONTSIZE = 20

BRANCHE_ARROWHEAD = {  # depends on branch type
    2: 'curve',
    4: 'tee',
    5: 'odot',
    6: 'diamond',
    15: 'box',
    'default': 'normal'
}

BRANCHE_ARROWSTYLE = {  # depends if is active
    True: 'solid',
    False: 'dashed',
}

BRANCHE_COLORS = {  # depends on branch type (taken from Fudaa-Crue rendering)
    1: '#ff0031',
    2: '#ce009c',
    4: '#ff9a00',
    5: '#00ffff',
    6: '#31cb00',
    12: '#ffff00',
    14: '#319aff',
    15: '#319aff',
    20: '#0030ff',
    'default': 'black'
}

BRANCHE_SIZE = {  # depends on branch type (minor bed is larger)
    1: 4,
    2: 4,
    14: 4,
    15: 4,
    20: 4,
    'default': 2
}

CASIER_SHAPE = {  # depends if it has a connected casier
    True: 'box3d',
    False: 'ellipse',
}

NODE_COLOR = {  # depends if it is active
    True: 'white',
    False: 'grey',
}

SM_STYLE = {  # depends if it is active
    True: 'normal',
    False: 'dashed',
}


def key_from_constant(key, CONSTANT):
    """Retourne la valeur de key du dictionnanire CONSTANT"""
    try:
        return CONSTANT[key]
    except KeyError:
        try:
            return CONSTANT['default']
        except KeyError:
            raise ExceptionCrue10("La clé '{}' n'existe pas".format(key))
