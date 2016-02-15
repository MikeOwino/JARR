from web.views import views, home, session_mgmt, api

from .article import article_bp, articles_bp
from .feed import feed_bp, feeds_bp
from .category import category_bp, categories_bp
from .icon import icon_bp
from .admin import admin_bp
from .user import user_bp, users_bp


__all__ = ['home', 'views', 'session_mgmt', 'api',
           'article_bp', 'articles_bp', 'feed_bp', 'feeds_bp', 'category_bp',
           'categories_bp', 'icon_bp', 'admin_bp', 'user_bp', 'users_bp']
