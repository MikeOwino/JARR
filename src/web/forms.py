#! /usr/bin/env python
# -*- coding: utf-8 -*-

# jarr - A Web based news aggregator.
# Copyright (C) 2010-2013  Cédric Bonhomme - https://www.JARR-aggregator.org
#
# For more information : http://github.com/JARR-aggregator/JARR/
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>

__author__ = "Cedric Bonhomme"
__version__ = "$Revision: 0.3 $"
__date__ = "$Date: 2013/11/05 $"
__revision__ = "$Date: 2015/05/06 $"
__copyright__ = "Copyright (c) Cedric Bonhomme"
__license__ = "GPLv3"


from flask import flash, url_for, redirect
from flask.ext.wtf import Form
from flask.ext.babel import lazy_gettext
from wtforms import TextField, TextAreaField, PasswordField, BooleanField, \
        SubmitField, IntegerField, SelectField, validators, HiddenField
from flask.ext.wtf.html5 import EmailField
from flask_wtf import RecaptchaField

from web import utils
from web.models import User


class SignupForm(Form):
    """
    Sign up form (registration to jarr).
    """
    nickname = TextField(lazy_gettext("Nickname"),
            [validators.Required(lazy_gettext("Please enter your nickname."))])
    email = EmailField(lazy_gettext("Email"),
            [validators.Length(min=6, max=35),
             validators.Required(
                 lazy_gettext("Please enter your email address."))])
    password = PasswordField(lazy_gettext("Password"),
            [validators.Required(lazy_gettext("Please enter a password.")),
             validators.Length(min=6, max=100)])
    recaptcha = RecaptchaField()
    submit = SubmitField(lazy_gettext("Sign up"))

    def validate(self):
        validated = super(SignupForm, self).validate()
        if self.nickname.data != User.make_valid_nickname(self.nickname.data):
            self.nickname.errors.append(lazy_gettext(
                    'This nickname has invalid characters. '
                    'Please use letters, numbers, dots and underscores only.'))
            validated = False
        return validated


class RedirectForm(Form):
    """
    Secure back redirects with WTForms.
    """
    next = HiddenField()

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        if not self.next.data:
            self.next.data = utils.get_redirect_target() or ''

    def redirect(self, endpoint='home', **values):
        if utils.is_safe_url(self.next.data):
            return redirect(self.next.data)
        target = utils.get_redirect_target()
        return redirect(target or url_for(endpoint, **values))


class SigninForm(RedirectForm):
    """
    Sign in form (connection to jarr).
    """
    email = EmailField("Email", [validators.Length(min=6, max=35),
        validators.Required(lazy_gettext("Please enter your email address."))])
    password = PasswordField(lazy_gettext('Password'),
            [validators.Required(lazy_gettext("Please enter a password.")),
             validators.Length(min=6, max=100)])
    submit = SubmitField(lazy_gettext("Log In"))

    def validate(self):
        if not super(SigninForm, self).validate():
            return False

        user = User.query.filter(User.email == self.email.data).first()
        if user and user.check_password(self.password.data) \
                and user.activation_key == "":
            return True
        elif user and user.activation_key != "":
            flash(lazy_gettext('Account not confirmed'), 'danger')
            return False
        else:
            flash(lazy_gettext('Invalid email or password'), 'danger')
            return False


class UserForm(Form):
    """
    Create or edit a user (for the administrator).
    """
    nickname = TextField(lazy_gettext("Nickname"),
            [validators.Required(lazy_gettext("Please enter your nickname."))])
    email = EmailField(lazy_gettext("Email"),
               [validators.Length(min=6, max=35),
                validators.Required(lazy_gettext("Please enter your email."))])
    password = PasswordField(lazy_gettext("Password"))
    refresh_rate = IntegerField(lazy_gettext("Feeds refresh frequency "
                                             "(in minutes)"),
                                default=60)
    submit = SubmitField(lazy_gettext("Save"))

    def validate(self):
        validated = super(UserForm, self).validate()
        if self.nickname.data != User.make_valid_nickname(self.nickname.data):
            self.nickname.errors.append(lazy_gettext(
                    'This nickname has invalid characters. '
                    'Please use letters, numbers, dots and underscores only.'))
            validated = False
        return validated


class ProfileForm(Form):
    """
    Edit user information.
    """
    nickname = TextField(lazy_gettext("Nickname"),
            [validators.Required(lazy_gettext("Please enter your nickname."))])
    email = EmailField(lazy_gettext("Email"),
               [validators.Length(min=6, max=35),
                validators.Required(lazy_gettext("Please enter your email."))])
    password = PasswordField(lazy_gettext("Password"))
    password_conf = PasswordField(lazy_gettext("Password Confirmation"))
    refresh_rate = IntegerField(lazy_gettext("Feeds refresh frequency "
                                             "(in minutes)"),
                                default=60)

    readability_key = TextField(lazy_gettext("Readability API key"))
    submit = SubmitField(lazy_gettext("Save"))

    def validate(self):
        validated = super().validate()
        if self.password.data != self.password_conf.data:
            message = lazy_gettext("Passwords aren't the same.")
            self.password.errors.append(message)
            self.password_conf.errors.append(message)
            validated = False
        if self.nickname.data != User.make_valid_nickname(self.nickname.data):
            self.nickname.errors.append(lazy_gettext('This nickname has '
                    'invalid characters. Please use letters, numbers, dots and'
                    ' underscores only.'))
            validated = False
        return validated


class AddFeedForm(Form):
    title = TextField(lazy_gettext("Title"), [validators.Optional()])
    link = TextField(lazy_gettext("Feed link"),
            [validators.Required(lazy_gettext("Please enter the URL."))])
    site_link = TextField(lazy_gettext("Site link"), [validators.Optional()])
    enabled = BooleanField(lazy_gettext("Check for updates"), default=True)
    submit = SubmitField(lazy_gettext("Save"))
    category_id = SelectField(lazy_gettext("Category of the feed"),
                              [validators.Optional()])

    def set_category_choices(self, categories):
        self.category_id.choices = [('0', 'No Category')]
        self.category_id.choices += [(str(cat.id), cat.name)
                                      for cat in categories]


class CategoryForm(Form):
    name = TextField(lazy_gettext("Name"))
    submit = SubmitField(lazy_gettext("Submit"))


class InformationMessageForm(Form):
    subject = TextField(lazy_gettext("Subject"),
            [validators.Required(lazy_gettext("Please enter a subject."))])
    message = TextAreaField(lazy_gettext("Message"),
            [validators.Required(lazy_gettext("Please enter a content."))])
    submit = SubmitField(lazy_gettext("Send"))


class RecoverPasswordForm(Form):
    email = EmailField(lazy_gettext("Email"),
            [validators.Length(min=6, max=35),
             validators.Required(
                 lazy_gettext("Please enter your email address."))])
    submit = SubmitField(lazy_gettext("Recover"))

    def validate(self):
        if not super(RecoverPasswordForm, self).validate():
            return False

        user = User.query.filter(User.email == self.email.data).first()
        if user and user.activation_key == "":
            return True
        elif user and user.activation_key != "":
            flash(lazy_gettext('Account not confirmed.'), 'danger')
            return False
        else:
            flash(lazy_gettext('Invalid email.'), 'danger')
            return False
