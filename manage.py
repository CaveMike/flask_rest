#!venv/bin/python
import json
import logging
import os
import unittest

import secrets
from app import *

class TestManage(unittest.TestCase):
    MODELS = [Group, User, UserToGroup, Device, Publication, Subscription, Message]

    def setUp(self):
        self.db = SqliteDatabase('peewee.db')
        self.db.connect()

    def tearDown(self):
        self.db.close()

    def testReCreate(self):
        for model in self.MODELS:
            model.delete().execute()

        self.db.create_tables(self.MODELS, safe=True)

        # Groups
        admin = Group.create(name='admin')
        user = Group.create(name='user')
        guest = Group.create(name='guest')

        # Users
        admin = User.create_user(name='Administrator', description='Administrator', email='admin@localhost.com', username='admin', password='1234')
        Device.create(user=admin, name='d2', resource='work', type='computer', dev_id='a')

        chloe = User.create_user(name='Chloe', username='chloe', password='1234')
        d = chloe.create_device(name='d2', resource='work', type='computer', dev_id='a')
        chloe.create_device(name='d0', resource='home', type='phone', dev_id='b')
        chloe.create_device(name='d3', resource='home', type='laptop', dev_id='c')
        chloe.create_device(name='d1', resource='work', type='phone', dev_id='d')
        UserToGroup.create(user=chloe, group=guest)

        sunshine = User.create_user(name='Sunshine', username='sunshine', password='1234')
        sunshine.create_device(name='d5', resource='work', type='phone', dev_id='e')
        UserToGroup.create(user=sunshine, group=user)
        UserToGroup.create(user=sunshine, group=guest)
        p = Publication.create(user=sunshine, topic='Life and Times of Sunshine', description='', group=guest)
        Message.create(user=sunshine, to_publication=p, subject='First post!')
        Message.create(user=sunshine, to_publication=p, subject='Eating breakfast')
        Message.create(user=sunshine, to_publication=p, subject='Time for a nap')

        guinness = User.create_user(name='Guinness', username='guinness', password='1234')
        guinness.create_device(name='d7', resource='work', type='phone', dev_id='g')
        UserToGroup.create(user=guinness, group=guest)

        felix = User.create_user(name='Felix', username='felix', password='1234')
        felix.create_device(name='d6', resource='work', type='phone', dev_id='f')
        UserToGroup.create(user=felix, group=guest)
        Subscription.create(user=felix, publication=p)
        Message.create(user=felix, to_publication=p, subject='boring...')
        Message.create(user=felix, to_user=sunshine, subject='hi sunshine')
        Message.create(user=felix, to_device=d, subject='hi chloe')
        Message.create(user=felix, to_user=chloe, subject='hi chloe again')

        ducky = User.create_user(name='Ducky', username='ducky', password='1234')
        ducky.create_device(name='d8', resource='work', type='phone', dev_id='h')
        UserToGroup.create(user=ducky, group=admin)
        UserToGroup.create(user=ducky, group=user)
        UserToGroup.create(user=ducky, group=guest)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(module)s.%(funcName)s#%(lineno)d %(message)s')
    unittest.main()