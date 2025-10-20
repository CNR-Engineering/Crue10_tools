import os.path


DATA_TESTS_FOLDER_ABSPATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'data')

DEFAULT_METADATA = {
    'AuteurCreation': 'USERNAME',
    'DateCreation': '2000-01-01T00:00:00.000',
    'AuteurDerniereModif': 'USERNAME',
    'DateDerniereModif': '2000-01-01T00:00:00.000',
}

WRITE_REFERENCE_FILES = False
