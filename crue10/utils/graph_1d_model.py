from crue10.utils import CrueError


# Branches
TYPE_BRANCHES = {
    'BranchePdc': '1',
    'BrancheSeuilTransversal': '2',
    'BrancheSeuilLateral': '4',
    'BrancheOrifice': '5',
    'BrancheStrickler': '6',
    'BrancheNiveauxAssocies': '12',
    'BrancheBarrageGenerique': '14',
    'BrancheBarrageFilEau': '15',
    'BrancheSaintVenant': '20',
}

# Flèches selon le type de branche
ARROWHEAD = {
    '2': 'curve',
    '4': 'tee',
    '5': 'odot',
    '6': 'diamond',
    '15': 'box',
    'default': 'normal'
    # 'BrancheNiveauxAssocies': '?',
}

# Couleurs selon le type de branche
COLORS = {
    '4': 'darkgreen',
    '5': 'green',
    '6': 'purple',
    '9': 'navy',
    '20': 'blue',
    'default': 'black'
}

# Taille selon le type de branche
SIZE = {
    '9': 4,
    '15': 4,
    '20': 4,
    'default': 2
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
