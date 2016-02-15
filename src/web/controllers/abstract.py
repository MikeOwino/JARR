import logging
from flask.ext.login import current_user
from bootstrap import db
from sqlalchemy import or_, func
from werkzeug.exceptions import Forbidden, NotFound

logger = logging.getLogger(__name__)


class AbstractController(object):
    _db_cls = None  # reference to the database class
    _user_id_key = 'user_id'

    def __init__(self, user_id=None, ignore_context=False):
        """User id is a right management mechanism that should be used to
        filter objects in database on their denormalized "user_id" field
        (or "id" field for users).
        Should no user_id be provided, the Controller won't apply any filter
        allowing for a kind of "super user" mode.
        """
        try:
            self.user_id = int(user_id)
        except TypeError:
            self.user_id = user_id
        # if we have context and it's a common user
        # requesting on a wrong id, we update that id
        have_context = False
        if not ignore_context:
            have_context = bool(current_user)
        wide_controller = self.user_id is None
        if have_context and not wide_controller \
                and self.user_id != current_user.id \
                and not current_user.is_admin:
            self.user_id = current_user.id

    def _to_filters(self, **filters):
        """
        Will translate filters to sqlalchemy filter.
        This method will also apply user_id restriction if available.

        each parameters of the function is treated as an equality unless the
        name of the parameter ends with either "__gt", "__lt", "__ge", "__le",
        "__ne", "__in" ir "__like".
        """
        db_filters = set()
        for key, value in filters.items():
            if key == '__or__':
                db_filters.add(or_(*self._to_filters(**value)))
            elif key.endswith('__gt'):
                db_filters.add(getattr(self._db_cls, key[:-4]) > value)
            elif key.endswith('__lt'):
                db_filters.add(getattr(self._db_cls, key[:-4]) < value)
            elif key.endswith('__ge'):
                db_filters.add(getattr(self._db_cls, key[:-4]) >= value)
            elif key.endswith('__le'):
                db_filters.add(getattr(self._db_cls, key[:-4]) <= value)
            elif key.endswith('__ne'):
                db_filters.add(getattr(self._db_cls, key[:-4]) != value)
            elif key.endswith('__in'):
                db_filters.add(getattr(self._db_cls, key[:-4]).in_(value))
            elif key.endswith('__like'):
                db_filters.add(getattr(self._db_cls, key[:-6]).like(value))
            elif key.endswith('__ilike'):
                db_filters.add(getattr(self._db_cls, key[:-7]).ilike(value))
            else:
                db_filters.add(getattr(self._db_cls, key) == value)
        return db_filters

    def _get(self, **filters):
        """ Will add the current user id if that one is not none (in which case
        the decision has been made in the code that the query shouldn't be user
        dependant) and the user is not an admin and the filters doesn't already
        contains a filter for that user.
        """
        if self._user_id_key is not None and self.user_id \
                and filters.get(self._user_id_key) != self.user_id:
            filters[self._user_id_key] = self.user_id
        return self._db_cls.query.filter(*self._to_filters(**filters))

    def get(self, **filters):
        """Will return one single objects corresponding to filters"""
        obj = self._get(**filters).first()

        if obj and not self._has_right_on(obj):
            raise Forbidden({'message': 'No authorized to access %r (%r)'
                                % (self._db_cls.__class__.__name__, filters)})
        if not obj:
            raise NotFound({'message': 'No %r (%r)'
                                % (self._db_cls.__class__.__name__, filters)})
        return obj

    def create(self, **attrs):
        if self._user_id_key is not None and self._user_id_key not in attrs:
            attrs[self._user_id_key] = self.user_id
        assert self._user_id_key is None or self._user_id_key in attrs \
                or self.user_id is None, \
                "You must provide user_id one way or another"

        obj = self._db_cls(**attrs)
        db.session.add(obj)
        db.session.commit()
        return obj

    def read(self, **filters):
        return self._get(**filters)

    def update(self, filters, attrs):
        result = self._get(**filters).update(attrs, synchronize_session=False)
        db.session.commit()
        return result

    def delete(self, obj_id):
        obj = self.get(id=obj_id)
        db.session.delete(obj)
        db.session.commit()
        return obj

    def _has_right_on(self, obj):
        # user_id == None is like being admin
        if self._user_id_key is None:
            return True
        return self.user_id is None \
                or getattr(obj, self._user_id_key, None) == self.user_id

    def _count_by(self, elem_to_group_by, filters):
        if self.user_id:
            filters['user_id'] = self.user_id
        return dict(db.session.query(elem_to_group_by, func.count('id'))
                              .filter(*self._to_filters(**filters))
                              .group_by(elem_to_group_by).all())
