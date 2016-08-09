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

    def add_group(self, group):
        return UserToGroup.add_user_to_group(group=group, user=self)

    def __str__(self):
        return 'name={}, description={}, email={}, username={}, password={}'.format(self.name, self.description, self.email, self.username, self.password)

class UserSchema(BaseSchema):
    name = fields.Str(required=True)
    description = fields.Str(required=True)
    email = fields.Str(required=True)
    username = fields.Str(required=True)
    password = fields.Str(required=True)

class Group(BaseModel):
    name = CharField()
    description = CharField(default='')

    owner = ForeignKeyField(User, related_name='owned_groups')

    def is_owner(self, user):
        return self.owner == user

    def is_member(self, user):
        return UserToGroup.is_member(group=self, user=user)

    def add_user(self, user):
        return UserToGroup.add_user_to_group(group=self, user=user)

    def __str__(self):
        return 'name={}, description={}, owner_id={}, owner.name={}'.format(self.name, self.description, self.owner_id, self.owner.name)

class GroupSchema(BaseSchema):
    name = fields.Str(required=True)
    description = fields.Str(required=True)

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
    publish_group = ForeignKeyField(Group, related_name='publications')
    subscribe_group = ForeignKeyField(Group, related_name='subscriptions')

    @property
    def parent_id(self):
        return self.user.id

    def is_owner(self, user):
        return self.user == user

    def can_publish(self, user):
        return self.publish_group.is_member(user)

    def can_subscribe(self, user):
        return self.subscribe_group.is_member(user)

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


class UserToGroup(BaseModel):
    """A simple "through" table for many-to-many relationship."""

    class Meta:
        primary_key = CompositeKey('user', 'group')

    user = ForeignKeyField(User)
    group = ForeignKeyField(Group)

    @classmethod
    def add_user_to_group(cls, group, user):
        if UserToGroup.is_member(group=group, user=user):
            logging.error('User already member of group: group={}, user={}'.format(group, user))
            return False

        return UserToGroup.create(group=group, user=user)

    @classmethod
    def is_member(cls, group, user):
        logging.debug('group={}, user={}'.format(group, user))
        query = UserToGroup.select().where(UserToGroup.user == user, UserToGroup.group == group)
        if len(query) == 0:
            return False
        elif len(query) == 1:
            return True
        else:
            raise Exception('Invalid UserToGroup query length, query={}'.format(len(query)))

    def __str__(self):
        return 'user={}, group={}'.format(self.user.name, self.group.name)



class TestModel(unittest.TestCase):
    def setUp(self):
        self.db = SqliteDatabase('peewee.db')
        self.db.connect()

        self.db.create_tables([Device, Group, User, UserToGroup, Publication], safe=True)

        Device.delete().execute()
        Group.delete().execute()
        User.delete().execute()
        UserToGroup.delete().execute()
        Publication.delete().execute()

        self.user0 = User.create_user(name='user0name', username='user0username', password='user0password')
        self.user0.create_device(name='device0name', resource='device0resource', type='device0type', dev_id='device0id', reg_id='device0regid')

        self.user1 = User.create_user(name='user1name', username='user1username', password='user1password')
        self.user1.create_device(name='device1name', resource='device1resource', type='device1type', dev_id='device1id')

        self.group0 = Group.create(name='group0name', description='group0description', owner=self.user0)
        self.group0.add_user(user=self.user0)
        self.group0.add_user(user=self.user1)

        self.group1 = Group.create(name='group1name', description='group1description', owner=self.user0)
        self.group1.add_user(user=self.user0)

        self.group2 = Group.create(name='group2name', description='group2description', owner=self.user1)
        self.group2.add_user(user=self.user1)

        self.pub0 = Publication.create(user=self.user0, topic='pub0topic', description='pub0description', publish_group=self.group1, subscribe_group=self.group0)

    def tearDown(self):
        self.db.close()
        self.db = None

    def test_group_get(self):
        os = Group.select()
        self.assertEqual(len(os), 3)

        o = Group.select().where(Group.name == 'group0name').get()
        self.assertEqual(o, self.group0)

        o = Group.select().where(Group.id == self.group0.id).get()
        self.assertEqual(o, self.group0)
        self.assertTrue(o.owner_id)

    def test_group_memberships(self):
        self.assertTrue(self.group0.is_member(self.user0))
        self.assertTrue(self.group0.is_member(self.user1))

        self.assertTrue(self.group1.is_member(self.user0))
        self.assertFalse(self.group1.is_member(self.user1))

        self.assertFalse(self.group2.is_member(self.user0))
        self.assertTrue(self.group2.is_member(self.user1))

    def test_get_reg_ids_by_user_id(self):
        user_id = self.user0.id

        devices = Device.select(Device, User).join(User).where(User.id == user_id)
        self.assertEqual(len(devices), 1)

        reg_ids = [d.reg_id for d in devices]
        self.assertEqual(reg_ids, ['device0regid'])

ALL_MODELS = \
[
    Config,
    Device,
    Group,
    Message,
    Publication,
    Subscription,
    User,
    UserToGroup,
]

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(module)s.%(funcName)s#%(lineno)d %(message)s')
    unittest.main()