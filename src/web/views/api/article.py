from conf import API_ROOT
import dateutil.parser
from flask import current_app
from flask.ext.restful import Api

from web.controllers import ArticleController
from web.views.api.common import (PyAggAbstractResource,
        PyAggResourceNew, PyAggResourceExisting, PyAggResourceMulti)


ARTICLE_ATTRS = {'user_id': {'type': int},
                 'feed_id': {'type': int},
                 'category_id': {'type': int},
                 'entry_id': {'type': str},
                 'link': {'type': str},
                 'title': {'type': str},
                 'readed': {'type': bool},
                 'like': {'type': bool},
                 'content': {'type': str},
                 'date': {'type': str},
                 'retrieved_date': {'type': str}}


class ArticleNewAPI(PyAggResourceNew):
    controller_cls = ArticleController
    attrs = ARTICLE_ATTRS
    to_date = ['date', 'retrieved_date']


class ArticleAPI(PyAggResourceExisting):
    controller_cls = ArticleController
    attrs = ARTICLE_ATTRS
    to_date = ['date', 'retrieved_date']


class ArticlesAPI(PyAggResourceMulti):
    controller_cls = ArticleController
    attrs = ARTICLE_ATTRS
    to_date = ['date', 'retrieved_date']


class ArticlesChallenge(PyAggAbstractResource):
    controller_cls = ArticleController
    attrs = {'ids': {'type': list, 'default': []}}
    to_date = ['date', 'retrieved_date']

    def get(self):
        parsed_args = self.reqparse_args()
        for id_dict in parsed_args['ids']:
            for key in self.to_date:
                if key in id_dict:
                    id_dict[key] = dateutil.parser.parse(id_dict[key])

        result = list(self.wider_controller.challenge(parsed_args['ids']))
        return result or None, 200 if result else 204

api = Api(current_app, prefix=API_ROOT)

api.add_resource(ArticleNewAPI, '/article', endpoint='article_new.json')
api.add_resource(ArticleAPI, '/articles/<int:obj_id>', endpoint='article.json')
api.add_resource(ArticlesAPI, '/articles', endpoint='articles.json')
api.add_resource(ArticlesChallenge, '/articles/challenge',
                 endpoint='articles_challenge.json')
