import os.path
import unittest

from crue10.etude import Etude
from crue10.tests import DATA_TESTS_FOLDER_ABSPATH
from crue10.utils.settings import VERSION_GRAMMAIRE_COURANTE


class EtudeTestCase(unittest.TestCase):

    def setUp(self):
        folder_in = os.path.join(DATA_TESTS_FOLDER_ABSPATH, 'in', VERSION_GRAMMAIRE_COURANTE)
        self.etude_3_6 = Etude(os.path.join(folder_in, 'Etu3-6_grammaire', 'Etu3-6.etu.xml'))
        self.etude_from_scratch = Etude(os.path.join(folder_in, 'Etu_from_scratch', 'Etu_from_scratch.etu.xml'))

    def test_details(self):
        self.assertEqual(self.etude_3_6.details(), """# Liste des scénarios
- Sc_M3-6_c10

# Liste des modèles
- Mo_M3-6_c10

# Liste des sous-modèles
- Sm_M3-6_c10

# Arborescence des Sc/Mo/Sm
Etu3-6
└── Sc_M3-6_c10
    └── Mo_M3-6_c10
        └── Sm_M3-6_c10""")

        self.assertEqual(self.etude_from_scratch.details(), """# Liste des scénarios
- Sc_multi_avec_bgefileau
- Sc_multi_avec_bgegenerique
- Sc_mono_sm

# Liste des modèles
- Mo_multi_avec_bgefileau
- Mo_multi_avec_bgegenerique
- Mo_mono_sm

# Liste des sous-modèles
- Sm_amont
- Sm_CAS
- Sm_CAA
- Sm_bgefileau
- Sm_bgegenerique
- Sm_mono_sm

# Arborescence des Sc/Mo/Sm
Etu_from_scratch
├── Sc_multi_avec_bgefileau
│   └── Mo_multi_avec_bgefileau
│       ├── Sm_amont
│       ├── Sm_CAS
│       ├── Sm_CAA
│       └── Sm_bgefileau
├── Sc_multi_avec_bgegenerique
│   └── Mo_multi_avec_bgegenerique
│       ├── Sm_amont
│       ├── Sm_CAS
│       ├── Sm_CAA
│       └── Sm_bgegenerique
└── Sc_mono_sm
    └── Mo_mono_sm
        └── Sm_mono_sm""")
