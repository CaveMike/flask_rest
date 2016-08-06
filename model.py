#!venv/bin/python
import datetime
import logging
import uuid
import unittest

from flask import url_for

from marshmallow import fields
#from marshmallow import pprint
#from marshmallow import pre_load
#from marshmallow import post_load
#from marshmallow import pre_dump
#from marshmallow import post_dump
#from marshmallow import validate
from marshmallow import Schema

from pbkdf2 import crypt

from peewee import CharField
from peewee import CompositeKey
from peewee import DateTimeField
from peewee import ForeignKeyField
from peewee import IntegerField
from peewee import Model
from peewee import SqliteDatabase

class BaseModel(Model):
    created = DateTimeField(default=datetime.datetime.now)
    modified = DateTimeField(default=datetime.datetime.now)
    revision = IntegerField(default=0)

    @property
    def endpoint(self):
        return self.__class__.__name__.lower() + 's'

    @property
    def parent_id(self):
        return None

    @property
    def uri(self):
        return url_for(endpoint=self.endpoint, id=self.id, parent=self.parent_id, _external=True)

    def save(self, *args, **kwargs):
        self.modified = datetime.datetime.now()
        self.revision += 1
        super(BaseModel, self).save(*args, **kwargs)

    def __str__(self):
        return 'id={}, uri={}, created={}, modified={}, revision={}'.format(self.id, self.uri, self.created, self.modified, self.revision)

class BaseSchema(Schema):
    class Meta:
        ordered = True

    id = fields.Int(dump_only=True)
    created = fields.DateTime(dump_only=True)
    modified = fields.DateTime(dump_only=True)
    revision = fields.Int(dump_only=True)

    uri = fields.Str(dump_only=True)

class Config(BaseModel):
    app_api_key = CharField()
    messaging_api_key = CharField()

class ConfigSchema(BaseSchema):
    app_api_key = fields.Str(required=True)
    messaging_api_key = fields.Str(required=True)

class Group(BaseModel):
    name = CharField()
    description = CharField(default='')

    def __str__(self):
        return 'name={}'.format(self.name)

class GroupSchema(BaseSchema):
    name = fields.Str(required=True)
    description = fields.Str(required=True)

class User(BaseModel):
    name = CharField()
    description = CharField(default='')
    email = CharField(default='')
    username = CharField(default='')
    password = CharField(default='')

    @classmethod
    def crypt_password(cls, username, password):
        encrypted_password = crypt(password)
        logging.debug('password={}, encrypted_password={}'.format(password, encrypted_password))
        return encrypted_password

    @classmethod
    def create_user(cls, username, password, **kwargs):
        encrypted_password = User.crypt_password(username, password)
        logging.debug('get_password: username={}, password={}, encrypted_password={}'.format(username, password, encrypted_password))
        return User.create(username=username, password=encrypted_password, **kwargs)

    def create_device(self, **kwargs):
        return Device.create(user=self, **kwargs)

    def __str__(self):
        return 'name={}, description={}, email={}, username={}, password={}'.format(self.name, self.description, self.email, self.username, self.password)

class UserSchema(BaseSchema):
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    email = fields.Str(required=True)
    username = fields.Str(required=True)
    password = fields.Str(required=True)

class UserToGroup(BaseModel):
    """A simple "through" table for many-to-many relationship."""

    class Meta:
        primary_key = CompositeKey('user', 'group')

    user = ForeignKeyField(User)
    group = ForeignKeyField(Group)

    def __str__(self):
        return 'user={}, group={}'.format(self.user.name, self.group.name)

class Device(BaseModel):
    name = CharField()
    dev_id = CharField(default='')
    reg_id = CharField(default='')
    resource = CharField(default='')
    type = CharField(default='')

    user = ForeignKeyField(User, related_name='devices')

    @property
    def parent_id(self):
        return self.user.id

    def __str__(self):
        return 'name={}, dev_id={}, reg_id={}, resource={}, type={}, user={}'.format(self.name, self.dev_id, self.reg_id, self.resource, self.type, self.user.name)

class DeviceSchema(BaseSchema):
    name = fields.Str(required=True)
    dev_id = fields.Str(required=True)
    reg_id = fields.Str(required=True)
    resource = fields.Str(required=True)
    type = fields.Str(required=True)

class Publication(BaseModel):
    topic = CharField()
    description = CharField(default='')

    user = ForeignKeyField(User, related_name='publications')
    group = ForeignKeyField(Group, related_name='publications')

    @property
    def parent_id(self):
        return self.user.id

    def __str__(self):
        return 'topic={}, description={}, user={}'.format(self.topic, self.description, self.user.name)

class PublicationSchema(BaseSchema):
    topic = fields.Str(required=True)
    description = fields.Str(required=True)

class Subscription(BaseModel):
    user = ForeignKeyField(User, related_name='subscriptions')
    publication = ForeignKeyField(Publication, related_name='subscriptions')

    @property
    def parent_id(self):
        return self.user.id

    def __str__(self):
        return 'user={}, pub={}'.format(self.user.name, self.publication.topic)

class SubscriptionSchema(BaseSchema):
    pass

class Message(BaseModel):
    class Meta:
        order_by = ('-modified', )

    user = ForeignKeyField(User, related_name='tx_messages')

    to_user = ForeignKeyField(User, related_name='rx_messages', null=True)
    to_device = ForeignKeyField(Device, related_name='rx_messages', null=True)
    to_publication = ForeignKeyField(Publication, related_name='rx_messages', null=True)
    subject = CharField()
    body = CharField(default='')

    @property
    def parent_id(self):
        return self.user.id

    def __str__(self):
        a = ['subject={}, body={}, from_user={}'.format(self.subject, self.body, self.user.name)]

        if self.to_user:
            a.append('to_user={}'.format(self.to_user.name))

        if self.to_device:
            a.append('to_device={}'.format(self.to_device.name))

        if self.to_publication:
            a.append('to_publication={}'.format(self.to_publication.topic))

        return ', '.join(a)

class MessageSchema(BaseSchema):
    subject = fields.Str(required=True)
    body = fields.Str(required=True)

class TestGroup(unittest.TestCase):
    def setUp(self):
        self.db = SqliteDatabase('test.db')
        self.db.connect()

        Group.delete().execute()

        admin = Group.create(name='test')
        user = Group.create(name='user')
        guest = Group.create(name='guest')

    def tearDown(self):
        self.db.close()
        self.db = None

    def test_get_all(self):
        os = Group.select()
        self.assertEqual(len(os), 3)

    def test_get_one(self):
        o0 = Group.select().where(Group.name == 'test').get()
        self.assertTrue(o0)
        self.assertEqual(o0.name, 'test')

        o1 = Group.select().where(Group.id == o0.id).get()
        self.assertTrue(o1)
        self.assertEqual(o0, o1)

class TestUser(unittest.TestCase):
    def setUp(self):
        self.db = SqliteDatabase('test.db')
        self.db.connect()

        User.delete().execute()
        Device.delete().execute()

        self.fake0 = User.create_user(name='fake0', username='fake0', password='fake0')
        self.fake0.create_device(name='d10', resource='work', type='computer', dev_id='a')

        self.user = User.create_user(name='Chloe', username='chloe', password='password')
        self.user.create_device(name='d2', resource='work', type='computer', dev_id='a', reg_id='r2')
        self.user.create_device(name='d0', resource='home', type='phone', dev_id='b', reg_id='r0')
        self.user.create_device(name='d3', resource='home', type='laptop', dev_id='c', reg_id='r3')
        self.user.create_device(name='d1', resource='work', type='phone', dev_id='d', reg_id='r1')

        self.fake1 = User.create_user(name='fake1', username='fake1', password='fake1')
        self.fake1.create_device(name='d20', resource='work', type='computer', dev_id='a')

    def tearDown(self):
        self.db.close()
        self.db = None

    def test_get_reg_ids_by_user_id(self):
        user_id = self.user.id

        devices = Device.select(Device, User).join(User).where(User.id == user_id)
        self.assertEqual(len(devices), 4)

        reg_ids = [d.reg_id for d in devices]
        self.assertEqual(reg_ids, ['r2', 'r0', 'r3', 'r1'])

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(module)s.%(funcName)s#%(lineno)d %(message)s')
    unittest.main()