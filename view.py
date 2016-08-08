#!venv/bin/python
import logging

from flask import request
from flask.views import MethodView

from flask_httpauth import HTTPBasicAuth

from seq_tools import to_sequence_or_set

class View(MethodView):
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