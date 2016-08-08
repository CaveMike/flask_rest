#!venv/bin/python
import logging

import werkzeug.routing

from flask import abort
from flask import redirect
from flask import Flask
from flask import jsonify
from flask import make_response

from flask_httpauth import HTTPBasicAuth

from pbkdf2 import crypt

from playhouse.flask_utils import FlaskDB

import model
from view import View

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s.%(msecs)d %(levelname)s %(threadName)s(%(thread)d) %(module)s.%(funcName)s#%(lineno)d %(message)s', datefmt='%d.%m.%Y %H:%M:%S')

app = Flask(__name__, static_url_path = '')

database = FlaskDB(app, 'sqlite:///peewee.db')

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, alleged_password):
    try:
        user = model.User.select().where(model.User.username == username).get()
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

def prepare_routes(base_url='/api/v1.0/'):
    View.decorators = [auth.login_required]

    View.add(app, base_url=[base_url + 'configs'], endpoint='configs', model_cls=model.Config, schema_cls=model.ConfigSchema)

    View.add(app, base_url=[base_url + 'groups'], endpoint='groups', model_cls=model.Group, schema_cls=model.GroupSchema)

    View.add(app, base_url=[base_url + 'users'], endpoint='users', model_cls=model.User, schema_cls=model.UserSchema)

    View.add(app, base_url=[base_url + 'users/<string:parent>/devices', base_url + 'devices'], endpoint='devices', model_cls=model.Device, schema_cls=model.DeviceSchema, parent_cls=model.User)
    View.add(app, base_url=base_url + 'users/<string:user_id>/devices/<string:parent>/messages', endpoint='devices.messages', model_cls=model.Message, schema_cls=model.MessageSchema, parent_cls=model.Device)

    View.add(app, base_url=[base_url + 'users/<string:parent>/publications', base_url + 'publications'], endpoint='publications', model_cls=model.Publication, schema_cls=model.PublicationSchema, parent_cls=model.User)
    View.add(app, base_url=base_url + 'users/<string:user_id>/publications/<string:parent>/subscriptions', endpoint='publication.subscriptions', model_cls=model.Subscription, schema_cls=model.SubscriptionSchema, parent_cls=model.Publication)
    View.add(app, base_url=base_url + 'users/<string:user_id>/publications/<string:parent>/messages', endpoint='publication.messages', model_cls=model.Message, schema_cls=model.MessageSchema, parent_cls=model.Publication)

    View.add(app, base_url=[base_url + 'users/<string:parent>/susbscriptions', base_url + 'subscriptions'], endpoint='subscriptions', model_cls=model.Subscription, schema_cls=model.SubscriptionSchema, parent_cls=model.User)
    #View.add(app, base_url=base_url + 'users/<string:user_id>/susbscriptions/<string:parent>/messages', endpoint='subscription.messages', model_cls=model.Message, schema_cls=model.MessageSchema, parent_cls=model.Subscription)

    View.add(app, base_url=[base_url + 'users/<string:parent>/messages', base_url + 'messages'], endpoint='messages', model_cls=model.Message, schema_cls=model.MessageSchema, parent_cls=model.User)

if __name__ == '__main__':
    prepare_routes()
    app.run(debug=True)
