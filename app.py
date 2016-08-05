#!venv/bin/python
import logging

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

from pbkdf2 import crypt

from playhouse.flask_utils import FlaskDB

import model

from seq_tools import is_sequence_or_set
from seq_tools import to_sequence_or_set

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

def prepare_routes(base_url='/api/v1.0/'):
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
