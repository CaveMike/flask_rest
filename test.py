#!venv/bin/python
import json
import logging
import os
import unittest

from base64 import b64encode

import app

class TestBase(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()
        app.prepare_database()

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
        response = self.request('GET', '/api/v1.0/users/', auth=('admin', '1234'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(len(j), 6)

    def test_get_one(self):
        response = self.request('GET', '/api/v1.0/users/3', auth=('admin', '1234'))
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

        response = self.request('POST', '/api/v1.0/users/', auth=('admin', '1234'), json_data=json_data)
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

        response = self.request('POST', '/api/v1.0/users/', auth=('admin', '1234'), json_data=json_data)
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

        response = self.request('PUT', '/api/v1.0/users/3', auth=('admin', '1234'), json_data=json_data)
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

        response = self.request('PATCH', '/api/v1.0/users/3', auth=('admin', '1234'), json_data=json_data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(j['uri'], 'http://localhost/api/v1.0/users/3')

    def test_delete_all(self):
        response = self.request('DELETE', '/api/v1.0/users/', auth=('admin', '1234'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(len(j), 6)
        self.assertEqual(j[0]['uri'], 'http://localhost/api/v1.0/users/1')

    def test_delete_one(self):
        response = self.request('DELETE', '/api/v1.0/users/3', auth=('admin', '1234'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        print(j)
        self.assertEqual(j['uri'], 'http://localhost/api/v1.0/users/3')

class TestDevice(TestBase):
    def test_get_all(self):
        response = self.request('GET', '/api/v1.0/users/2/devices/', auth=('admin', '1234'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(len(j), 4)

    def test_get_one(self):
        response = self.request('GET', '/api/v1.0/users/2/devices/4', auth=('admin', '1234'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(j['uri'], 'http://localhost/api/v1.0/users/2/devices/4')

class TestGroup(TestBase):
    def test_get_all(self):
        response = self.request('GET', '/api/v1.0/groups/', auth=('admin', '1234'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(len(j), 3)

    def test_get_one(self):
        response = self.request('GET', '/api/v1.0/groups/1', auth=('admin', '1234'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertTrue(response.content_length)

        j = json.loads(response.data.decode('utf-8'))
        self.assertEqual(j['name'], 'admin')
        self.assertEqual(j['uri'], 'http://localhost/api/v1.0/groups/1')

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(module)s.%(funcName)s#%(lineno)d %(message)s')
    app.prepare_routes()
    unittest.main()