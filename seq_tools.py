#!/usr/bin/env python3
import unittest

def is_sequence(arg):
    return not hasattr(arg, 'strip') and hasattr(arg, '__getitem__') and hasattr(arg, '__iter__')

class TestIsSeq(unittest.TestCase):
    def test_string(self):
        self.assertFalse(is_sequence('test'))

    def test_tuple_string(self):
        self.assertTrue(is_sequence(('test', )))

    def test_tuple_strings(self):
        self.assertTrue(is_sequence(('test0', 'test1')))

    def test_list_string(self):
        self.assertTrue(is_sequence(['test', ]))

    def test_list_strings(self):
        self.assertTrue(is_sequence(['test0', 'test1']))

def to_sequence(arg):
    return arg if is_sequence(arg) else (arg, )

class TestToSeq(unittest.TestCase):
    def test_none(self):
        self.assertEqual(to_sequence(None), (None, ))

    def test_scalar(self):
        self.assertEqual(to_sequence(12), (12, ))

    def test_tuple(self):
        self.assertEqual(to_sequence((1, 2, 3)), (1, 2, 3))

    def test_list(self):
        self.assertEqual(to_sequence([1, 2, 3]), [1, 2, 3])

    def test_str(self):
        self.assertEqual(to_sequence('abc'), ('abc', ))

def is_sequence_or_set(arg):
    return isinstance(arg, set) or is_sequence(arg)

class TestIsSeqOrSet(unittest.TestCase):
    def test_set(self):
        self.assertTrue(is_sequence_or_set(set([1, 2, 3])))

    def test_set_string(self):
        self.assertTrue(is_sequence_or_set(set('test', )))

    def test_set_strings(self):
        self.assertTrue(is_sequence_or_set(set(('test0', 'test1'))))

def to_sequence_or_set(arg):
    return arg if is_sequence_or_set(arg) else (arg, )

class TestToSeqOrSet(unittest.TestCase):
    def test_set(self):
        self.assertEqual(to_sequence_or_set(set([1, 2, 3])), {1, 2, 3})

if __name__ == '__main__':
    unittest.main()