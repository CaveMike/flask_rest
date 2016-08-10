#!venv/bin/python
import json
import logging
import os
import unittest

from base64 import b64encode

from peewee import SqliteDatabase

from app import app
from app import prepare_routes

import model

from secrets import APP_API_KEY
from secrets import MESSAGING_API_KEY
from secrets import TEST_USER
from secrets import TEST_PASSWORD
from secrets import TEST_CREDENTIALS

class TestBase(unittest.TestCase):
    def populate_database(self):
        self.db = SqliteDatabase('peewee.db')
        self.db.connect()

        self.db.create_tables(model.ALL_MODELS, safe=True)

        for m in model.ALL_MODELS:
            m.delete().execute()

        self.db.close()

        # Config
        release = model.Config.create(app_api_key=APP_API_KEY, messaging_api_key=MESSAGING_API_KEY)

        admin_user = model.User.create_user(name='Administrator', description='Administrator', email='admin@localhost.com', username=TEST_USER, password=TEST_PASSWORD)

        # Groups
        admin = model.Group.create(name=TEST_USER, owner=admin_user)
        user = model.Group.create(name='user', owner=admin_user)
        guest = model.Group.create(name='guest', owner=admin_user)

        # Users
        model.Device.create(user=admin, name='d2', resource='work', type='computer', dev_id='a')

        chloe = model.User.create_user(name='Chloe', username='chloe', password=TEST_PASSWORD)
        d = chloe.create_device(name='d2', resource='work', type='computer', dev_id='a')
        chloe.create_device(name='d0', resource='home', type='phone', dev_id='b')
        chloe.create_device(name='d3', resource='home', type='laptop', dev_id='c')
        chloe.create_device(name='d1', resource='work', type='phone', dev_id='d')
        model.UserToGroup.create(user=chloe, group=guest)

        sunshine = model.User.create_user(name='Sunshine', username='sunshine', password=TEST_PASSWORD)
        sunshine.create_device(name='d5', resource='work', type='phone', dev_id='e')
        model.UserToGroup.create(user=sunshine, group=user)
        model.UserToGroup.create(user=sunshine, group=guest)
        p = model.Publication.create(user=sunshine, topic='Life and Times of Sunshine', description='', publish_group=guest, subscribe_group=guest)
        model.Message.create(user=sunshine, to_publication=p, subject='First post!')
        model.Message.create(user=sunshine, to_publication=p, subject='Eating breakfast')
        model.Message.create(user=sunshine, to_publication=p, subject='Time for a nap')

        guinness = model.User.create_user(name='Guinness', username='guinness', password=TEST_PASSWORD)
        guinness.create_device(name='d7', resource='work', type='phone', dev_id='g')
        model.UserToGroup.create(user=guinness, group=guest)

        felix = model.User.create_user(name='Felix', username='felix', password=TEST_PASSWORD)
        felix.create_device(name='d6', resource='work', type='phone', dev_id='f')
        model.UserToGroup.create(user=felix, group=guest)
        model.Subscription.create(user=felix, publication=p)
        model.Message.create(user=felix, to_publication=p, subject='boring...')
        model.Message.create(user=felix, to_user=sunshine, subject='hi sunshine')
        model.Message.create(user=felix, to_device=d, subject='hi chloe')
        model.Message.create(user=felix, to_user=chloe, subject='hi chloe again')

        ducky = model.User.create_user(name='Ducky', username='ducky', password=TEST_PASSWORD)
        ducky.create_device(name='d8', resource='work', type='phone', dev_id='h')
        model.UserToGroup.create(user=ducky, group=admin)
        model.UserToGroup.create(user=ducky, group=user)
        model.UserToGroup.create(user=ducky, group=guest)

    def setUp(self):
        self.app = app.test_client()
        self.populate_database()

    def request(self, method, url, auth=None, json_data=None, **kwargs):
        headers = kwargs.get('headers', {})

        if auth:
            # Add the auth header if credentials are specified.
            headers['Authorization'] = 'Basic %s' % b64encode(bytes(auth[0] + ':' + auth[1], 'utf-8')).decode('ascii')

        if json:
            headers['Content-Type'] = 'application/json'
            kwargs['data'] = json.dumps(obj=json_data)
            #print(kwargs['data'])

        kwargs['headers'] = headers
        #print(kwargs['headers'])

        return self.app.open(url, method=method, **kwargs)

class TestUser(TestBase):
    def test_get_all(self):
        response = self.request('GET', '/api/v1.0/users/', auth=TEST_CREDENTIALS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(len(j), 6)

    def test_get_one(self):
        response = self.request('GET', '/api/v1.0/users/3', auth=TEST_CREDENTIALS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(j['uri'], 'http://localhost/api/v1.0/users/3')

    def test_create_one(self):
        json_data = {
            'name' : 'Guinness',
            'description' : '',
            'email' : 'guinness@localhost.com',
            'username' : 'guinness',
            'password' : 'stout',
        }

        response = self.request('POST', '/api/v1.0/users/', auth=TEST_CREDENTIALS, json_data=json_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(j['uri'], 'http://localhost/api/v1.0/users/7')

    @unittest.skip
    def test_create_two(self):
        json_data = [
        {
            'name' : 'Buster',
        },
        {
            'name' : 'Lenny',
        }
        ]

        response = self.request('POST', '/api/v1.0/users/', auth=TEST_CREDENTIALS, json_data=json_data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(len(j), 2)
        self.assertEqual(j[0]['uri'], 'http://localhost/api/v1.0/users/5')
        self.assertEqual(j[1]['uri'], 'http://localhost/api/v1.0/users/6')

    def test_update_one(self):
        json_data = {
            'name' : 'Sunshine (a)',
            'description' : '',
            'email' : 'sunshine@localhost.com',
            'username' : 'sunshine',
            'password' : 'rhino',
        }

        response = self.request('PUT', '/api/v1.0/users/3', auth=TEST_CREDENTIALS, json_data=json_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(j['uri'], 'http://localhost/api/v1.0/users/3')

    def test_patch_one(self):
        json_data = {
            'name' : 'Sunshine (b)',
            'password' : 'horn',
        }

        response = self.request('PATCH', '/api/v1.0/users/3', auth=TEST_CREDENTIALS, json_data=json_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(j['uri'], 'http://localhost/api/v1.0/users/3')

    @unittest.skip
    def test_delete_all(self):
        response = self.request('DELETE', '/api/v1.0/users/', auth=TEST_CREDENTIALS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(len(j), 6)
        self.assertEqual(j[0]['uri'], 'http://localhost/api/v1.0/users/1')

    def test_delete_one(self):
        response = self.request('DELETE', '/api/v1.0/users/3', auth=TEST_CREDENTIALS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        print(j)
        self.assertEqual(j['uri'], 'http://localhost/api/v1.0/users/3')

class TestDevice(TestBase):
    def test_get_all(self):
        response = self.request('GET', '/api/v1.0/users/2/devices/', auth=TEST_CREDENTIALS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(len(j), 4)

    def test_get_one(self):
        response = self.request('GET', '/api/v1.0/users/2/devices/4', auth=TEST_CREDENTIALS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(j['uri'], 'http://localhost/api/v1.0/users/2/devices/4')

class TestGroup(TestBase):
    def test_get_all(self):
        response = self.request('GET', '/api/v1.0/groups/', auth=TEST_CREDENTIALS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(len(j), 3)

    def test_get_one(self):
        response = self.request('GET', '/api/v1.0/groups/1', auth=TEST_CREDENTIALS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(j['name'], TEST_USER)
        self.assertEqual(j['uri'], 'http://localhost/api/v1.0/groups/1')

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(module)s.%(funcName)s#%(lineno)d %(message)s')
    prepare_routes()
    unittest.main()