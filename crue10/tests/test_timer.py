# coding: utf-8
import time
import unittest

from crue10.utils.timer import time_it, activ_period


class TimerTestCase(unittest.TestCase):

    def setUp(self):
        # Il n'y a rien de spécial à définir ici
        pass

    def test_time_it(self):
        time_it(reinit=True)
        time.sleep(5)
        res = time_it()
        self.assertEqual(res.seconds, 5)

    def test_activ_period(self):
        activ_period(reinit=True)
        self.assertEqual(activ_period(period=3), False)
        self.assertEqual(activ_period(period=3), False)
        self.assertEqual(activ_period(period=3), True)
        self.assertEqual(activ_period(period=3), False)
        self.assertEqual(activ_period(period=3), False)
        self.assertEqual(activ_period(period=3), True)
