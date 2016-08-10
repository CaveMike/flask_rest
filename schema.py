#!venv/bin/python
import datetime
import logging
import uuid
import unittest

from marshmallow import fields
#from marshmallow import pprint
#from marshmallow import pre_load
#from marshmallow import post_load
#from marshmallow import pre_dump
#from marshmallow import post_dump
#from marshmallow import validate
from marshmallow import Schema

class BaseSchema(Schema):
    class Meta:
        ordered = True

    id = fields.Int(dump_only=True)
    created = fields.DateTime(dump_only=True)
    modified = fields.DateTime(dump_only=True)
    revision = fields.Int(dump_only=True)

    uri = fields.Str(dump_only=True)

class ConfigSchema(BaseSchema):
    app_api_key = fields.Str(required=True)
    messaging_api_key = fields.Str(required=True)

class UserSchema(BaseSchema):
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    email = fields.Str(required=True)
    username = fields.Str(required=True)
    password = fields.Str(required=True, load_only=True)

class GroupSchema(BaseSchema):
    name = fields.Str(required=True)
    description = fields.Str(required=True)

class DeviceSchema(BaseSchema):
    name = fields.Str(required=True)
    dev_id = fields.Str(required=True)
    reg_id = fields.Str(required=True)
    resource = fields.Str(required=True)
    type = fields.Str(required=True)

class PublicationSchema(BaseSchema):
    topic = fields.Str(required=True)
    description = fields.Str(required=True)

class SubscriptionSchema(BaseSchema):
    pass

class MessageSchema(BaseSchema):
    subject = fields.Str(required=True)
    body = fields.Str(required=True)

class TestSchema(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_all(self):
        pass

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(module)s.%(funcName)s#%(lineno)d %(message)s')
    unittest.main()