# coding: utf-8
import unittest

from crue10.utils.traceback import trace_except, cur_file, cur_func, cur_class, cur_meth


class TracebackTestCase(unittest.TestCase):

    def setUp(self):
        # Il n'y a rien de spécial à définir ici
        pass

    def test_trace_except_function(self):
        # Définir une inner-function de test
        @trace_except
        def test_exception():
            raise ValueError('Exception sur une fonction')

        # Conduire le test
        with self.assertRaises(ValueError) as cm:
            test_exception()
        self.assertEqual(isinstance(cm.exception, ValueError), True)
        self.assertEqual(cm.exception.args[0], 'Exception sur une fonction')

    def test_trace_except_method(self):
        # Définir une inner-class de test
        class TestException():
            def crash(self):
                raise ValueError('Exception sur une méthode')

        # Conduire le test
        with self.assertRaises(Exception) as cm:
            te = TestException()
            te.crash()
        self.assertEqual(isinstance(cm.exception, ValueError), True)
        self.assertEqual(cm.exception.args[0], 'Exception sur une méthode')

    def test_cur_file(self):
        self.assertEqual(cur_file(), 'C:\\PROJETS\\Crue10_tools\\crue10\\tests\\test_traceback.py')

    def test_cur_func(self):
        self.assertEqual(cur_func(), 'test_traceback.py\\test_cur_func')

    def test_cur_class(self):
        self.assertEqual(cur_class(), 'TracebackTestCase')

    def test_cur_meth(self):
        self.assertEqual(cur_meth(), 'TracebackTestCase.test_cur_meth')
