import string
import random
from flask import (Blueprint, render_template, redirect,
                   flash, url_for, request)
from flask.ext.babel import gettext
from flask.ext.login import current_user, login_required

import conf
from web import utils, notifications
from web.controllers import (UserController, FeedController, ArticleController)

from web.forms import ProfileForm, RecoverPasswordForm

users_bp = Blueprint('users', __name__, url_prefix='/users')
user_bp = Blueprint('user', __name__, url_prefix='/user')


@user_bp.route('/management', methods=['GET', 'POST'])
@login_required
def management():
    """
    Display the management page.
    """
    if request.method == 'POST':
        if request.files.get('opmlfile', None) is not None:
            # Import an OPML file
            data = request.files.get('opmlfile', None)
            if not utils.allowed_file(data.filename):
                flash(gettext('File not allowed.'), 'danger')
            else:
                try:
                    nb = utils.import_opml(current_user.email, data.read())
                    if conf.CRAWLING_METHOD == "classic":
                        utils.fetch(current_user.email, None)
                        flash(str(nb) + '  ' + gettext('feeds imported.'),
                                "success")
                        flash(gettext("Downloading articles..."), 'info')
                except:
                    flash(gettext("Impossible to import the new feeds."),
                            "danger")
        elif request.files.get('jsonfile', None) is not None:
            # Import an account
            data = request.files.get('jsonfile', None)
            if not utils.allowed_file(data.filename):
                flash(gettext('File not allowed.'), 'danger')
            else:
                try:
                    nb = utils.import_json(current_user.login, data.read())
                    flash(gettext('Account imported.'), "success")
                except:
                    flash(gettext("Impossible to import the account."),
                            "danger")
        else:
            flash(gettext('File not allowed.'), 'danger')

    nb_feeds = FeedController(current_user.id).read().count()
    art_contr = ArticleController(current_user.id)
    nb_articles = art_contr.read().count()
    nb_unread_articles = art_contr.read(readed=False).count()
    return render_template('management.html', user=current_user,
                            nb_feeds=nb_feeds, nb_articles=nb_articles,
                            nb_unread_articles=nb_unread_articles)


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    Edit the profile of the currently logged user.
    """
    user_contr = UserController(current_user.id)
    user = user_contr.get(id=current_user.id)
    form = ProfileForm()

    if request.method == 'POST':
        if form.validate():
            user_contr.update({'id': current_user.id},
                              {'login': form.login.data,
                               'email': form.email.data,
                               'password': form.password.data,
                               'refresh_rate': form.refresh_rate.data})

            flash(gettext('User %(login)s successfully updated',
                          login=user.login), 'success')
            return redirect(url_for('user.profile'))
        else:
            return render_template('profile.html', user=user, form=form)

    if request.method == 'GET':
        form = ProfileForm(obj=user)
        return render_template('profile.html', user=user, form=form)


@user_bp.route('/delete_account', methods=['GET'])
@login_required
def delete_account():
    """
    Delete the account of the user (with all its data).
    """
    UserController(current_user.id).delete(current_user.id)
    flash(gettext('Your account has been deleted.'), 'success')
    return redirect(url_for('login'))


@user_bp.route('/recover', methods=['GET', 'POST'])
def recover():
    """
    Enables the user to recover its account when he has forgotten
    its password.
    """
    form = RecoverPasswordForm()
    user_contr = UserController()

    if request.method == 'POST':
        if form.validate():
            user = user_contr.get(email=form.email.data)
            characters = string.ascii_letters + string.digits
            password = "".join(random.choice(characters)
                               for x in range(random.randint(8, 16)))
            user.set_password(password)
            user_contr.update({'id': user.id}, {'password': password})

            # Send the confirmation email
            try:
                notifications.new_password_notification(user, password)
                flash(gettext('New password sent to your address.'), 'success')
            except Exception as error:
                flash(gettext('Problem while sending your new password: '
                              '%(error)s', error=error), 'danger')

            return redirect(url_for('login'))
        return render_template('recover.html', form=form)

    if request.method == 'GET':
        return render_template('recover.html', form=form)
