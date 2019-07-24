# coding: utf-8
from crue10.utils import CrueError


SM_FONTSIZE = 40

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

BRANCHE_COLORS = {  # depends on branch type
    1: 'red',
    4: 'darkgreen',
    5: 'green',
    6: 'purple',
    9: 'navy',
    20: 'blue',
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

NODE_BGCOLOR = {  # depends if it is active
    True: 'white',
    False: 'grey',
}


def key_from_constant(key, CONSTANT):
    """Retourne la valeur de key du dictionnanire CONSTANT"""
    try:
        return CONSTANT[key]
    except KeyError:
        try:
            return CONSTANT['default']
        except KeyError:
            raise CrueError("La clé '{}' n'existe pas".format(key))
