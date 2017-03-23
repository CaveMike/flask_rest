#!venv/bin/python
import logging

from functools import wraps

import werkzeug.routing

from flask import abort
from flask import redirect
from flask import Flask
from flask import g
from flask import jsonify
from flask import make_response

from flask_httpauth import HTTPBasicAuth

from pbkdf2 import crypt

from playhouse.flask_utils import FlaskDB

from adapter import Adapter
from model import ALL_MODELS
from model import Config
from model import Device
from model import Group
from model import Message
from model import Publication
from model import Subscription
from model import User
from schema import ConfigSchema
from schema import DeviceSchema
from schema import GroupSchema
from schema import MessageSchema
from schema import PublicationSchema
from schema import SubscriptionSchema
from schema import UserSchema
from view import View

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)d %(levelname)s %(threadName)s(%(thread)d) %(module)s.%(funcName)s#%(lineno)d %(message)s', datefmt='%d.%m.%Y %H:%M:%S')

app = Flask(__name__, static_url_path = '')

database = FlaskDB(app, 'sqlite:///peewee.db')

auth = HTTPBasicAuth()

class AuthExt:
    @classmethod
    def save(cls, user, **kwargs):
        g.current_user = user if user else None
        admin_group = Group.select().where(Group.name == 'admin').get()
        g.is_admin = admin_group.is_member(g.current_user)

    @classmethod
    def is_admin(cls, *args, **kwargs):
        logging.debug('args={}, kwargs={}, g={}'.format(args, kwargs, g))
        try:
            return g.is_admin
        except:
            logging.exception('is_admin missing')

        return False

    @classmethod
    def is_parent_user(cls, *args, **kwargs):
        logging.debug('args={}, kwargs={}, g={}'.format(args, kwargs, g))
        try:
            if int(kwargs['parent']) == g.current_user.id:
                return True
        except KeyError:
            logging.exception('parent not specified')
        except TypeError:
            logging.exception('invalid parent type')
        except:
            logging.exception('parent not user')

        return False

    @staticmethod
    def admin_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            logging.debug('args={}, kwargs={}'.format(args, kwargs))

            if AuthExt.is_admin(*args, **kwargs):
                return f(*args, **kwargs)

            return unauthorized()
        return decorated

    @staticmethod
    def admin_or_parent(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            logging.debug('args={}, kwargs={}'.format(id, args, kwargs))

            if AuthExt.is_admin(*args, **kwargs):
                return f(*args, **kwargs)

            if AuthExt.is_parent_user(*args, **kwargs):
                return f(*args, **kwargs)

            return unauthorized()
        return decorated

@auth.verify_password
def verify_password(username, alleged_password):
    try:
        user = User.select().where(User.username == username).get()
        verification = (crypt(alleged_password, user.password) == user.password)
        logging.debug('verify_password: username={}, encrypted_password={}, alleged_password={}, verification={}'.format(username, user.password, alleged_password, verification))

        if verification:
            AuthExt.save(user=user)

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

def prepare_routes(base_url='/api/v1.0/'):
    View.decorators = [AuthExt.admin_or_parent, auth.login_required]

    # Admin-only.
    View.add(app, base_url=[base_url + 'configs'], endpoint='configs', adapter=Adapter(model_cls=Config), schema_cls=ConfigSchema)

    View.add(app, base_url=[base_url + 'groups'], endpoint='groups', adapter=Adapter(model_cls=Group), schema_cls=GroupSchema)

    View.add(app, base_url=[base_url + 'users'], endpoint='users', adapter=Adapter(model_cls=User), schema_cls=UserSchema)

    View.add(app, base_url=[base_url + 'users/<string:parent>/devices', base_url + 'devices'], endpoint='devices', adapter=Adapter(model_cls=Device, parent_cls=User), schema_cls=DeviceSchema)
    View.add(app, base_url=base_url + 'users/<string:user_id>/devices/<string:parent>/messages', endpoint='devices.messages', adapter=Adapter(model_cls=Message, parent_cls=Device), schema_cls=MessageSchema)

    View.add(app, base_url=[base_url + 'users/<string:parent>/publications', base_url + 'publications'], endpoint='publications', adapter=Adapter(model_cls=Publication, parent_cls=User), schema_cls=PublicationSchema)
    View.add(app, base_url=base_url + 'users/<string:user_id>/publications/<string:parent>/subscriptions', endpoint='publication.subscriptions', adapter=Adapter(model_cls=Subscription, parent_cls=Publication), schema_cls=SubscriptionSchema)
    View.add(app, base_url=base_url + 'users/<string:user_id>/publications/<string:parent>/messages', endpoint='publication.messages', adapter=Adapter(model_cls=Message, parent_cls=Publication), schema_cls=MessageSchema)

    View.add(app, base_url=[base_url + 'users/<string:parent>/subscriptions', base_url + 'subscriptions'], endpoint='subscriptions', adapter=Adapter(model_cls=Subscription, parent_cls=User), schema_cls=SubscriptionSchema)
    #View.add(app, base_url=base_url + 'users/<string:user_id>/subscriptions/<string:parent>/messages', endpoint='subscription.messages', adapter=Adapter(model_cls=Message, parent_cls=Subscription), schema_cls=MessageSchema)

    View.add(app, base_url=[base_url + 'users/<string:parent>/messages', base_url + 'messages'], endpoint='messages', adapter=Adapter(model_cls=Message, parent_cls=User), schema_cls=MessageSchema)

if __name__ == '__main__':
    prepare_routes()
    app.run(debug=True)
