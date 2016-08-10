#!venv/bin/python
import json
import logging
import os
import unittest

from peewee import SqliteDatabase

from model import ALL_MODELS

class TestManage(unittest.TestCase):
    def setUp(self):
        self.db = SqliteDatabase('peewee.db')
        self.db.connect()

    def tearDown(self):
        self.db.close()

    def testCreate(self):
        self.db.create_tables(ALL_MODELS, safe=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(module)s.%(funcName)s#%(lineno)d %(message)s')
    unittest.main()