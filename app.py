#!venv/bin/python
import datetime
import logging
import uuid

import secrets

import werkzeug.routing

from flask import abort
from flask import redirect
from flask import Flask
from flask import jsonify
from flask import make_response
from flask import request
from flask import url_for

from flask.views import MethodView

from flask_httpauth import HTTPBasicAuth

from seq_tools import is_sequence_or_set
from seq_tools import to_sequence_or_set

from marshmallow import fields
from marshmallow import pprint
#from marshmallow import pre_load
#from marshmallow import post_load
#from marshmallow import pre_dump
#from marshmallow import post_dump
from marshmallow import validate
from marshmallow import Schema

from pbkdf2 import crypt

from peewee import *

from playhouse.flask_utils import FlaskDB

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)d %(levelname)s %(threadName)s(%(thread)d) %(module)s.%(funcName)s#%(lineno)d %(message)s', datefmt='%d.%m.%Y %H:%M:%S')

app = Flask(__name__, static_url_path = '')

database = FlaskDB(app, 'sqlite:///peewee.db')

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, alleged_password):
    try:
        user = User.select().where(User.username == username).get()
        verification = (crypt(alleged_password, user.password) == user.password)
        logging.debug('verify_password: username={}, encrypted_password={}, alleged_password={}, verification={}'.format(username, user.password, alleged_password, verification))
        return verification
    except Exception as e:
        logging.exception('verify_password')
        return False

@auth.error_handler
def unauthorized():
    # return 403 instead of 401 to prevent browsers from displaying the default auth dialog
    return make_response(jsonify({'error': 'Unauthorized access'}), 403)

@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.route('/')
@auth.login_required
def index():
    return redirect('/index.html')

class View(MethodView):
    decorators = [auth.login_required]

    def __init__(self, model_cls, schema_cls, parent_cls, **kwargs):
        super(View, self).__init__()

        self.model_cls=model_cls
        self.schema_cls=schema_cls
        self.parent_cls=parent_cls

        self.schema=schema_cls()
        self.schema_many=schema_cls(many=True)

    def get(self, id, parent=None, **kwargs):
        logging.debug('id={}, parent={}, kwargs={}'.format(id, parent, kwargs))

        if id:
            try:
                o = self.model_cls.select().where(self.model_cls.id == id).get()
                mresults = self.schema.dumps(o)
            except DoesNotExist as e:
                abort(404)
        else:
            query = self.model_cls.select()
            if self.parent_cls and parent:
                query = query.join(self.parent_cls).where(self.parent_cls.id == parent)

            mresults = self.schema_many.dumps(query)

        if mresults.errors:
            abort(404)

        return mresults.data, 200, {'Content-Type': 'application/json'}

    def post(self, id, parent=None, **kwargs):
        logging.debug('id={}, parent={}, kwargs={}'.format(id, parent, kwargs))

        if not request.json:
            abort(400)

        # Add query strings to json data.
        request.json.update(kwargs)

        errors = self.schema.validate(request.json, partial=False)
        logging.debug('errors={}'.format(errors))
        if errors:
            abort(400)

        model = self.model_cls.create(**request.json)

        mresults = self.schema.dumps(model)
        if mresults.errors:
            abort(404)

        return mresults.data, 201, {'Content-Type': 'application/json'}

    def __update(self, partial, id, parent=None, **kwargs):
        logging.debug('partial={}, id={}, parent={}, kwargs={}'.format(partial, id, parent, kwargs))

        if not request.json:
            abort(400)

        errors = self.schema.validate(request.json, partial=partial)
        logging.debug('errors={}'.format(errors))
        if errors:
            abort(400)

        try:
            o = self.model_cls.select().where(self.model_cls.id == id).get()
        except:
            abort(404)

        for (k, v) in request.json.items():
            o.__setattr__(k, v)

        o.save()

        mresults = self.schema.dumps(o)
        if mresults.errors:
            abort(404)

        return mresults.data, 200, {'Content-Type': 'application/json'}

    def put(self, id, parent=None, **kwargs):
        logging.debug('id={}, parent={}, kwargs={}'.format(id, parent, kwargs))
        return self.__update(partial=False, id=id, parent=parent, **kwargs)

    def patch(self, id, parent=None, **kwargs):
        logging.debug('id={}, parent={}, kwargs={}'.format(id, parent, kwargs))
        return self.__update(partial=True, id=id, parent=parent, **kwargs)

    def delete(self, id, parent=None, **kwargs):
        logging.debug('id={}, parent={}, kwargs={}'.format(id, parent, kwargs))

        if id:
            try:
                o = self.model_cls.select().where(self.model_cls.id == id).get()

                self.model_cls.delete_instance(o)

                mresults = self.schema.dumps(o)
            except DoesNotExist as e:
                abort(404)
        else:
            query = self.model_cls.select()

            os = []
            for o in query:
                self.model_cls.delete_instance(o)
                os.append(o)

            mresults = self.schema_many.dumps(os)

        if mresults.errors:
            abort(404)

        return mresults.data, 200, {'Content-Type': 'application/json'}

    @classmethod
    def add(cls, app, base_url, endpoint, model_cls, schema_cls, parent_cls=None):
        for endpoint in to_sequence_or_set(endpoint):
            view_func = View.as_view(endpoint, model_cls=model_cls, schema_cls=schema_cls, parent_cls=parent_cls)

            for base_url in to_sequence_or_set(base_url):
                methods = ('GET', 'POST', 'DELETE')
                url = base_url + '/'
                logging.debug('methods={}, url={}'.format(methods, url))
                app.add_url_rule(url, methods=methods, defaults={'id' : None}, view_func=view_func)

                methods = ('GET', 'PUT', 'PATCH', 'DELETE')
                url = base_url + '/<string:id>'
                logging.debug('methods={}, url={}'.format(methods, url))
                app.add_url_rule(url, methods=methods, defaults={}, view_func=view_func)

class BaseModel(database.Model):
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

def prepare_routes(base_url='/api/v1.0/'):
    View.add(app, base_url=[base_url + 'groups'], endpoint='groups', model_cls=Group, schema_cls=GroupSchema)

    View.add(app, base_url=[base_url + 'users'], endpoint='users', model_cls=User, schema_cls=UserSchema)

    View.add(app, base_url=[base_url + 'users/<string:parent>/devices', base_url + 'devices'], endpoint='devices', model_cls=Device, schema_cls=DeviceSchema, parent_cls=User)
    View.add(app, base_url=base_url + 'users/<string:user_id>/devices/<string:parent>/messages', endpoint='devices.messages', model_cls=Message, schema_cls=MessageSchema, parent_cls=Device)

    View.add(app, base_url=[base_url + 'users/<string:parent>/publications', base_url + 'publications'], endpoint='publications', model_cls=Publication, schema_cls=PublicationSchema, parent_cls=User)
    View.add(app, base_url=base_url + 'users/<string:user_id>/publications/<string:parent>/subscriptions', endpoint='publication.subscriptions', model_cls=Subscription, schema_cls=SubscriptionSchema, parent_cls=Publication)
    View.add(app, base_url=base_url + 'users/<string:user_id>/publications/<string:parent>/messages', endpoint='publication.messages', model_cls=Message, schema_cls=MessageSchema, parent_cls=Publication)

    View.add(app, base_url=[base_url + 'users/<string:parent>/susbscriptions', base_url + 'subscriptions'], endpoint='subscriptions', model_cls=Subscription, schema_cls=SubscriptionSchema, parent_cls=User)
    #View.add(app, base_url=base_url + 'users/<string:user_id>/susbscriptions/<string:parent>/messages', endpoint='subscription.messages', model_cls=Message, schema_cls=MessageSchema, parent_cls=Subscription)

    View.add(app, base_url=[base_url + 'users/<string:parent>/messages', base_url + 'messages'], endpoint='messages', model_cls=Message, schema_cls=MessageSchema, parent_cls=User)

def prepare_database():
    db = SqliteDatabase('peewee.db')
    db.connect()
    db.create_tables([Group, User, UserToGroup, Device, Publication, Subscription, Message], safe=True)

    # Delete
    Group.delete().execute()
    User.delete().execute()
    UserToGroup.delete().execute()
    Device.delete().execute()
    Publication.delete().execute()
    Subscription.delete().execute()
    Message.delete().execute()

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

    db.close()

if __name__ == '__main__':
    prepare_database()
    prepare_routes()
    app.run(debug=True)
