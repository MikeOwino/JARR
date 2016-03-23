#!/usr/bin/python3
import sys
from datetime import datetime, timedelta
from flask.ext.script import Command, Option

from web.controllers \
        import UserController, FeedController, ArticleController
DEFAULT_HEADERS = {'Content-Type': 'application/json', 'User-Agent': 'munin'}
LATE_AFTER = 60
FETCH_RATE = 3


class AbstractMuninPlugin(Command):
    urn = None

    def execute(self):
        raise NotImplementedError()

    def config(self):
        raise NotImplementedError()

    def get_options(self):
        if sys.argv[-1] == 'config':
            return [Option(dest='config', default=sys.argv[-1] == 'config')]
        return []

    def run(self, config=False):
        if config:
            self.config()
        else:
            self.execute()


class FeedProbe(AbstractMuninPlugin):

    def config(self):
        print("graph_title PyAgg - Feeds counts")
        print("graph_vlabel feeds")
        print("feeds.label Late feeds")
        print("feeds_total.label Total feeds")
        print("feeds.warning 15")
        print("feeds.critical 30")
        print("graph_category web")
        print("graph_scale yes")

    def execute(self):
        minutes = LATE_AFTER + FETCH_RATE + 1
        delta = datetime.utcnow() - timedelta(minutes=minutes)
        fcontr = FeedController(ignore_context=True)
        total = fcontr.read().count()

        print("feeds.value %d" % len(fcontr.list_late(delta, limit=total)))
        print("feeds_total.value %d" % fcontr.read().count())


class ArticleProbe(AbstractMuninPlugin):

    def config(self):
        print("graph_title JARR - Articles adding rate")
        print("graph_vlabel Articles per sec")
        print("articles.label Overall rate")
        print("articles.type DERIVE")
        print("articles.min 0")
        ucontr = UserController(ignore_context=True)
        for id_ in sorted(user.id for user in ucontr.read()):
            print("articles_user_%s.label Rate for user %s" % (id_, id_))
            print("articles_user_%s.type DERIVE" % id_)
            print("articles_user_%s.min 0" % id_)
        print("graph_category web")
        print("graph_scale yes")

    def execute(self):
        counts = ArticleController(ignore_context=True).count_by_user_id()
        print("articles.value %s" % sum(counts.values()))
        for user, count in counts.items():
            print("articles_user_%s.value %s" % (user, count))
