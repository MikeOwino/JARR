#! /usr/bin/env python
# -*- coding: utf-8 -*-

# jarr - A Web based news aggregator.
# Copyright (C) 2010-2016  Cédric Bonhomme - https://www.JARR-aggregator.org
#
# For more information : https://github.com/JARR-aggregator/JARR
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__author__ = "Cedric Bonhomme"
__version__ = "$Revision: 5.3 $"
__date__ = "$Date: 2010/01/29 $"
__revision__ = "$Date: 2014/08/27 $"
__copyright__ = "Copyright (c) Cedric Bonhomme"
__license__ = "AGPLv3"

import os
import logging
import datetime
from flask import jsonify
from calendar import timegm

from bootstrap import application as app, db

from flask import render_template, request, flash, session, \
                  url_for, redirect, g, current_app, make_response
from flask.ext.login import LoginManager, login_user, logout_user, \
                            login_required, current_user, AnonymousUserMixin
from flask.ext.principal import Principal, Identity, AnonymousIdentity, \
                                identity_changed, identity_loaded, Permission,\
                                RoleNeed, UserNeed
from flask.ext.babel import gettext
from sqlalchemy.exc import IntegrityError
from werkzeug import generate_password_hash

import conf
from web.lib.utils import redirect_url
from web import utils, notifications, export
from web.lib.view_utils import etag_match
from web.models import User, Article, Role
from web.forms import SignupForm, SigninForm

from web.controllers import UserController, FeedController, \
                            ArticleController, CategoryController

from plugins import readability


Principal(app)
# Create a permission with a single Need, in this case a RoleNeed.
admin_permission = Permission(RoleNeed('admin'))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_message = gettext('Authentication required.')
login_manager.login_message_category = "info"
login_manager.login_view = 'login'

logger = logging.getLogger(__name__)


#
# Management of the user's session.
#
@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Set the identity user object
    identity.user = current_user

    # Add the UserNeed to the identity
    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))

    # Assuming the User model has a list of roles, update the
    # identity with the roles that the user provides
    if hasattr(current_user, 'roles'):
        for role in current_user.roles:
            identity.provides.add(RoleNeed(role.name))


@app.before_request
def before_request():
    g.user = current_user
    if g.user.is_authenticated:
        g.user.last_seen = datetime.datetime.utcnow()
        db.session.add(g.user)
        db.session.commit()


@login_manager.user_loader
def load_user(id):
    # Return an instance of the User model
    return UserController().get(id=id)


#
# Custom error pages.
#
@app.errorhandler(401)
def authentication_required(e):
    flash(gettext('Authentication required.'), 'info')
    return redirect(url_for('login'))


@app.errorhandler(403)
def authentication_failed(e):
    flash(gettext('Forbidden.'), 'danger')
    return redirect(url_for('login'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('errors/500.html'), 500


@g.babel.localeselector
def get_locale():
    """
    Called before each request to give us a chance to choose
    the language to use when producing its response.
    """
    return request.accept_languages.best_match(conf.LANGUAGES.keys())


@g.babel.timezoneselector
def get_timezone():
    try:
        return conf.TIME_ZONE[get_locale()]
    except:
        return conf.TIME_ZONE["en"]


#
# Views.
#
@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Log in view.
    """
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('home'))
    g.user = AnonymousUserMixin()
    form = SigninForm()
    if form.validate_on_submit():
        user = UserController().get(email=form.email.data)
        login_user(user)
        g.user = user
        session['email'] = form.email.data
        identity_changed.send(current_app._get_current_object(),
                              identity=Identity(user.id))
        return form.redirect('home')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """
    Log out view. Removes the user information from the session.
    """
    session.pop('email', None)

    # Remove the user information from the session
    logout_user()

    # Remove session keys set by Flask-Principal
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    # Tell Flask-Principal the user is anonymous
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())

    flash(gettext("Logged out successfully."), 'success')
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """
    Signup page.
    """
    if int(os.environ.get("SELF_REGISTRATION", 0)) != 1:
        flash(gettext("Self-registration is disabled."), 'warning')
        return redirect(url_for('home'))
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('home'))

    form = SignupForm()

    if form.validate_on_submit():
        role_user = Role.query.filter(Role.name == "user").first()
        user = User(nickname=form.nickname.data,
                    email=form.email.data,
                    pwdhash=generate_password_hash(form.password.data))
        user.roles = [role_user]
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            flash(gettext('Email already used.'), 'warning')
            return render_template('signup.html', form=form)

        # Send the confirmation email
        try:
            notifications.new_account_notification(user)
        except Exception as error:
            flash(gettext('Problem while sending activation email: %(error)s',
                          error=error), 'danger')
            return redirect(url_for('home'))

        flash(gettext('Your account has been created. '
                      'Check your mail to confirm it.'), 'success')
        return redirect(url_for('home'))

    return render_template('signup.html', form=form)


@app.route('/')
@login_required
@etag_match
def home():
    return render_template('home.html', cdn=conf.CDN_ADDRESS)


@app.route('/menu')
@login_required
@etag_match
def get_menu():
    categories_order = [0]
    categories = {0: {'name': 'No category', 'id': 0}}
    for cat in CategoryController(g.user.id).read().order_by('name'):
        categories_order.append(cat.id)
        categories[cat.id] = cat.dump()
    unread = ArticleController(g.user.id).count_by_feed(readed=False)
    for cat_id in categories:
        categories[cat_id]['unread'] = 0
        categories[cat_id]['feeds'] = []
    feeds = {feed.id: feed.dump() for feed in FeedController(g.user.id).read()}
    for feed_id, feed in feeds.items():
        feed['created_stamp'] = timegm(feed['created_date'].timetuple()) * 1000
        feed['last_stamp'] = timegm(feed['last_retrieved'].timetuple()) * 1000
        feed['category_id'] = feed['category_id'] or 0
        feed['unread'] = unread.get(feed['id'], 0)
        if not feed['filters']:
            feed['filters'] = []
        if feed.get('icon_url'):
            feed['icon_url'] = url_for('icon.icon', url=feed['icon_url'])
        categories[feed['category_id']]['unread'] += feed['unread']
        categories[feed['category_id']]['feeds'].append(feed_id)
    return jsonify(**{'feeds': feeds, 'categories': categories,
                      'categories_order': categories_order,
                      'crawling_method': conf.CRAWLING_METHOD,
                      'max_error': conf.DEFAULT_MAX_ERROR,
                      'error_threshold': conf.ERROR_THRESHOLD,
                      'is_admin': g.user.is_admin(),
                      'all_unread_count': sum(unread.values())})


def _get_filters(in_dict):
    filters = {}
    query = in_dict.get('query')
    if query:
        search_title = in_dict.get('search_title') == 'true'
        search_content = in_dict.get('search_content') == 'true'
        if search_title:
            filters['title__ilike'] = "%%%s%%" % query
        if search_content:
            filters['content__ilike'] = "%%%s%%" % query
        if len(filters) == 0:
            filters['title__ilike'] = "%%%s%%" % query
        if len(filters) > 1:
            filters = {"__or__": filters}
    if in_dict.get('filter') == 'unread':
        filters['readed'] = False
    elif in_dict.get('filter') == 'liked':
        filters['like'] = True
    filter_type = in_dict.get('filter_type')
    if filter_type in {'feed_id', 'category_id'} and in_dict.get('filter_id'):
        filters[filter_type] = int(in_dict['filter_id']) or None
    return filters


def _articles_to_json(articles, fd_hash=None):
    return jsonify(**{'articles': [{'title': art.title, 'liked': art.like,
            'read': art.readed, 'article_id': art.id, 'selected': False,
            'feed_id': art.feed_id, 'category_id': art.category_id or 0,
            'feed_title': fd_hash[art.feed_id]['title'] if fd_hash else None,
            'icon_url': fd_hash[art.feed_id]['icon_url'] if fd_hash else None,
            'date': art.date, 'timestamp': timegm(art.date.timetuple()) * 1000}
            for art in articles.limit(1000)]})


@app.route('/middle_panel')
@login_required
@etag_match
def get_middle_panel():
    filters = _get_filters(request.args)
    art_contr = ArticleController(g.user.id)
    fd_hash = {feed.id: {'title': feed.title,
                         'icon_url': url_for('icon.icon', url=feed.icon_url)
                                     if feed.icon_url else None}
               for feed in FeedController(g.user.id).read()}
    articles = art_contr.read(**filters).order_by(Article.date.desc())
    return _articles_to_json(articles, fd_hash)


@app.route('/getart/<int:article_id>')
@app.route('/getart/<int:article_id>/<parse>')
@login_required
@etag_match
def get_article(article_id, parse=False):
    contr = ArticleController(g.user.id)
    article = contr.get(id=article_id).dump()
    if not article['readed']:
        contr.update({'id': article_id}, {'readed': True})
    article['category_id'] = article['category_id'] or 0
    feed = FeedController(g.user.id).get(id=article['feed_id'])
    article['icon_url'] = url_for('icon.icon', url=feed.icon_url) \
            if feed.icon_url else None
    readability_available = bool(g.user.readability_key
                                 or conf.READABILITY_KEY)
    article['readability_available'] = readability_available
    if parse or (not article['readability_parsed']
            and feed.readability_auto_parse and readability_available):
        article['readability_parsed'] = True
        article['content'] = readability.parse(article['link'],
                g.user.readability_key or conf.READABILITY_KEY)
        contr.update({'id': article['id']}, {'readability_parsed': True,
                                             'content': article['content']})
    return jsonify(**article)


@app.route('/mark_all_as_read', methods=['PUT'])
@login_required
def mark_all_as_read():
    filters, acontr = _get_filters(request.json), ArticleController(g.user.id)
    articles = _articles_to_json(acontr.read(**filters))
    acontr.update(filters, {'readed': True})
    return articles


@app.route('/fetch', methods=['GET'])
@app.route('/fetch/<int:feed_id>', methods=['GET'])
@login_required
def fetch(feed_id=None):
    """
    Triggers the download of news.
    News are downloaded in a separated process, mandatory for Heroku.
    """
    if conf.CRAWLING_METHOD == "classic" \
            and (not conf.ON_HEROKU or g.user.is_admin()):
        utils.fetch(g.user.id, feed_id)
        flash(gettext("Downloading articles..."), "info")
    else:
        flash(gettext("The manual retrieving of news is only available " +
                      "for administrator, on the Heroku platform."), "info")
    return redirect(redirect_url())


@app.route('/about', methods=['GET'])
@etag_match
def about():
    """
    'About' page.
    """
    return render_template('about.html')


@app.route('/export', methods=['GET'])
@login_required
def export_articles():
    """
    Export all articles to HTML or JSON.
    """
    user = UserController(g.user.id).get(id=g.user.id)
    if request.args.get('format') == "HTML":
        # Export to HTML
        try:
            archive_file, archive_file_name = export.export_html(user)
        except:
            flash(gettext("Error when exporting articles."), 'danger')
            return redirect(redirect_url())
        response = make_response(archive_file)
        response.headers['Content-Type'] = 'application/x-compressed'
        response.headers['Content-Disposition'] = 'attachment; filename=%s' \
                % archive_file_name
    elif request.args.get('format') == "JSON":
        # Export to JSON
        try:
            json_result = export.export_json(user)
        except:
            flash(gettext("Error when exporting articles."), 'danger')
            return redirect(redirect_url())
        response = make_response(json_result)
        response.mimetype = 'application/json'
        response.headers["Content-Disposition"] \
                = 'attachment; filename=account.json'
    else:
        flash(gettext('Export format not supported.'), 'warning')
        return redirect(redirect_url())
    return response


@app.route('/export_opml', methods=['GET'])
@login_required
def export_opml():
    """
    Export all feeds to OPML.
    """
    user = UserController(g.user.id).get(id=g.user.id)
    categories = {cat.id: cat.dump()
            for cat in CategoryController(g.user.id).read()}
    response = make_response(render_template('opml.xml', user=user,
                                            categories=categories,
                                            now=datetime.datetime.now()))
    response.headers['Content-Type'] = 'application/xml'
    response.headers['Content-Disposition'] = 'attachment; filename=feeds.opml'
    return response
