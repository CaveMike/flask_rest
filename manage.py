#!venv/bin/python
import json
import logging
import os
import unittest

import secrets
from app import *

class TestManage(unittest.TestCase):
    MODELS = [Config, Group, User, UserToGroup, Device, Publication, Subscription, Message]

    def setUp(self):
        self.db = SqliteDatabase('peewee.db')
        self.db.connect()

    def tearDown(self):
        self.db.close()

    def testCreate(self):
        self.db.create_tables(self.MODELS, safe=True)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(module)s.%(funcName)s#%(lineno)d %(message)s')
    unittest.main()