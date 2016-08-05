#!venv/bin/python
import json
import logging
import os
import unittest

from peewee import SqliteDatabase

import model

class TestManage(unittest.TestCase):
    MODELS = \
    [
        model.Config,
        model.Group,
        model.User,
        model.UserToGroup,
        model.Device,
        model.Publication,
        model.Subscription,
        model.Message,
    ]

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