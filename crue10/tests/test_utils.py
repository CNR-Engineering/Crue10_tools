import unittest

from crue10.utils import float2str


class BrancheTestCase(unittest.TestCase):

    def test_float2str(self):
        self.assertEqual(float2str(0), '0.0')
        self.assertEqual(float2str(0.0), '0.0')

        self.assertEqual(float2str(1234), '1234.0')
        self.assertEqual(float2str(1234.0), '1234.0')

        self.assertEqual(float2str(34.666664123535156), '34.666664123535156')
        self.assertEqual(float2str(1e30), '1.0E30')
        self.assertEqual(float2str(-1e30), '-1.0E30')
