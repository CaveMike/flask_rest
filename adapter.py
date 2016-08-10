#!venv/bin/python
import logging

class Adapter:
    def __init__(self, model_cls, parent_cls=None, **kwargs):
        self.model_cls = model_cls
        self.parent_cls = parent_cls

    def read_all(self, parent, **kwargs):
        query = self.model_cls.select()
        if self.parent_cls and parent:
            query = query.join(self.parent_cls).where(self.parent_cls.id == parent)

        return query

    def read_one(self, id, parent=None, **kwargs):
        try:
            return self.model_cls.select().where(self.model_cls.id == id).get()
        except self.model_cls.DoesNotExist as e:
            logging.exception('read_one failed')
            raise e

    def create_one(self, parent=None, **kwargs):
        return self.model_cls.create(**kwargs)

    def update_one(self, id, parent=None, **kwargs):
        o = self.model_cls.select().where(self.model_cls.id == id).get()

        for (k, v) in kwargs.items():
            o.__setattr__(k, v)

        o.save()
        return o

    def patch_one(self, id, parent=None, **kwargs):
        self.update_one(id=id, parent=parent, **kwargs)

    def delete_one(self, id, parent=None, **kwargs):
        o = self.read_one(id=id, parent=parent, **kwargs)
        if o:
            self.model_cls.delete_instance(o)
        return o

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s %(module)s.%(funcName)s#%(lineno)d %(message)s')
    unittest.main()