# coding: utf-8
import unittest

from crue10.utils.crueconfigmetier import CCM


class CCMTestCase(unittest.TestCase):

    def setUp(self):
        # CCM vient directement de 'crue10.utils.crueconfigmetier'
        pass

    def test_typ_num(self):
        self.assertEqual(CCM.typ_num['Tnu_Reel'].typ, float)
        self.assertEqual(CCM.typ_num['Tnu_Entier'].infini, 2000000000)

    def test_enum(self):
        self.assertEqual(CCM.enum['Ten_FormulePdc'].BORDA, 1)               # Appel d'Enum en tant que propriété
        self.assertEqual(CCM.enum['Ten_Etiquette']['Et_Thalweg'], 2)        # Appel d'Enum en tant que clé
        self.assertEqual(CCM.enum['Ten_Severite']['ERRNBLK'], 20)           # Enum, ex-ENUM_SEVERITE

    def test_nature(self):
        self.assertEqual(CCM.nature['Nat_Q'].unt, 'm^(3)/s')

    def test_constante(self):
        self.assertEqual(CCM.constante['DdPtgEpsilon'].nat.nom, 'Nat_D')    # Constante avec Nature
        self.assertEqual(CCM.constante['DdPtgEpsilon'].dft, 0.001)          # Constante avec Nature
        self.assertEqual(CCM.constante['ParamCalcEMHCasierProfil'].nat.nom, 'Nat_ParamCalc')        # Constante vecteur
        self.assertEqual(CCM.constante['ParamCalcEMHCasierProfil'].dft, '0.01 0.3 0.25 0.65 0.1')   # Constante vecteur

    def test_variable(self):
        self.assertEqual(CCM.variable['Pm_TolStQ'].dft, 0.01)               # Variable avec nature, ex-DEFAULT_Pm_TolStQ
        self.assertEqual(CCM.variable['FormulePdc'].nat.nom, 'Ten_FormulePdc')                      # Variable Enum
        self.assertEqual(CCM.variable['Beta'].nat.nom, 'Nat_Beta')          # Variable avec nature
        self.assertEqual(CCM.variable['FormulePdc'].dft, 0)                 # Variable Enum
        self.assertEqual(CCM.variable['FormulePdc'].dft.value, 0)           # Variable Enum
        self.assertEqual(CCM.variable['FormulePdc'].dft.name, 'DIVERGENT')  # Variable Enum
        self.assertEqual(CCM.variable['Beta'].dft, 1.0)                     # Variable avec nature
        self.assertEqual(CCM.variable['Qam'].txt(123., add_unt=True), '123.0000 m^(3)/s')           # Formatage variable
        self.assertEqual(CCM.variable['FormulePdc'].txt('DIVERGENT'), 'DIVERGENT(0)')               # Formatage Enum
        self.assertEqual(CCM.variable['CoefPdc'].valider(-1.),
            (False, "CoefPdc=-1.00000 est invalide: hors de l'intervalle [0.00000;+Infini]"))
        self.assertEqual(CCM.variable['CoefPdc'].valider(0.),
            (False, "CoefPdc=0.00000 est anormale: hors de l'intervalle [0.20000;1.00000]"))
        self.assertEqual(CCM.variable['CoefPdc'].valider(0.5), (True, ''))
        self.assertEqual(CCM.variable['CoefPdc'].valider(1.1),
            (False, "CoefPdc=1.10000 est anormale: hors de l'intervalle [0.20000;1.00000]"))
