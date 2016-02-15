# This file contains the export functions of jarr. Indeed
# it is possible to export the database of articles in different formats:
# - simple HTML webzine;
# - text file.
#

import os
import shutil
import time
import tarfile
from datetime import datetime

from flask import jsonify

import conf
from web import models


def HTML_HEADER(title="jarr", css="./style.css"):
    return """<!DOCTYPE html>
<html lang="en-US">
<head>
<title>%s</title>
<meta charset="utf-8"/>
<link rel="stylesheet" href="%s" />
</head>
<body>""" % (title, css)

HTML_FOOTER = """<hr />
<p>This archive has been generated with
<a href="https://github.com/JARR-aggregator/JARR">jarr</a>.
A software under AGPLv3 license.
You are welcome to copy, modify or redistribute the source code according to
the <a href="https://www.gnu.org/licenses/agpl-3.0.txt">AGPLv3</a> license.</p>
</body>
</html>
"""

CSS = """body {
    font:normal medium 'Gill Sans','Gill Sans MT',Verdana,sans-serif;
    margin:1.20em auto;
    width:80%;
    line-height:1.75;
}
blockquote {
    font-size:small;
    line-height:2.153846;
    margin:2.153846em 0;
    padding:0;font-style:oblique;
    border-left:1px dotted;
    margin-left:2.153846em;
    padding-left:2.153846em;
}
blockquote p{
    margin:2.153846em 0;
}
p+br {
    display:none;
}
h1 {
font-size:large;
}
h2,h3 {
    font-size:medium;
}
hr {
    border-style:dotted;
    height:1px;
    border-width: 1px 0 0 0;
    margin:1.45em 0 1.4em;
    padding:0;
}
a {
    text-decoration:none;
    color:#00008B;
}
#footer {
    clear:both;
    text-align:center;
    font-size:small;
}
img {
    border:0;
}
.horizontal,.simple li {
    margin:0;
    padding:0;
    list-style:none;
    display:inline
}
.simple li:before {
    content:"+ ";
}
.simple > li:first-child:before {
    content:"";
}
.author {
    text-decoration:none;
    display:block;
    float:right;
    margin-left:2em;
    font-size:small;
}
.content {
    margin:1.00em 1.00em;
}"""


def export_html(user):
    """
    Export all articles of 'user' in Web pages.
    """
    webzine_root = conf.WEBZINE_ROOT + "webzine/"
    nb_articles = format(len(models.Article.query.filter(
            models.Article.user_id == user.id).all()), ",d")
    index = HTML_HEADER("News archive")
    index += "<h1>List of feeds</h1>\n"
    index += """<p>%s articles.</p>\n<ul>\n""" % (nb_articles,)
    for feed in user.feeds.order_by(models.Feed.title):
        # creates a folder for each stream
        feed_folder = webzine_root + str(feed.id)
        try:
            os.makedirs(feed_folder)
        except OSError:
            # directories already exists (not a problem)
            pass

        index += '    <li><a href="%s">%s</a></li>\n' % (feed.id, feed.title)

        posts = HTML_HEADER(feed.title, "../style.css")
        posts += """<h1>Articles of the feed <a href="%s">%s</a></h1>\n""" % (
                feed.site_link, feed.title)
        posts += """<p>%s articles.</p>\n""" % (
                format(len(feed.articles.all()), ",d"),)

        for article in feed.articles:
            post_file_name = os.path.normpath(
                    feed_folder + "/" + str(article.id) + ".html")
            feed_index = os.path.normpath(feed_folder + "/index.html")

            posts += article.date.ctime() + ' - <a href="./%s.html">%s</a>' % \
                    (article.id, article.title[:150]) + "<br />\n"

            a_post = HTML_HEADER(article.title, "../style.css")
            a_post += '<div style="width:60%; overflow:hidden; '\
                    'text-align:justify; margin:0 auto">\n'
            a_post += """<h1><a href="%s">%s</a></h1>\n<br />""" % \
                        (article.link, article.title)
            a_post += article.content
            a_post += "</div>\n<hr />\n"
            a_post += '<br />\n<a href="%s">Complete story</a>\n<br />\n' \
                    % article.link
            a_post += HTML_FOOTER

            with open(post_file_name, "w") as f:
                f.write(a_post)

        posts += HTML_FOOTER
        if len(feed.articles.all()) != 0:
            with open(feed_index, "w") as f:
                f.write(posts)

    index += "</ul>\n"
    index += "<p>%s</p>" % time.strftime("Generated on %d %b %Y at %H:%M.")
    index += HTML_FOOTER
    with open(webzine_root + "index.html", "w") as f:
        f.write(index)
    with open(webzine_root + "style.css", "w") as f:
        f.write(CSS)

    archive_file_name = datetime.now().strftime('%Y-%m-%d') + '.tar.gz'
    with tarfile.open(conf.WEBZINE_ROOT + archive_file_name, "w:gz") as tar:
        tar.add(webzine_root, arcname=os.path.basename(webzine_root))

    shutil.rmtree(webzine_root)

    with open(conf.WEBZINE_ROOT + archive_file_name, 'rb') as export_file:
        return export_file.read(), archive_file_name


def export_json(user):
    """
    Export all articles of 'user' in JSON.
    """
    result = []
    for feed in user.feeds:
        result.append({
                "title": feed.title,
                "description": feed.description,
                "link": feed.link,
                "site_link": feed.site_link,
                "enabled": feed.enabled,
                "created_date": feed.created_date.strftime('%s'),
                "articles": [{
                    "title": article.title,
                    "link": article.link,
                    "content": article.content,
                    "readed": article.readed,
                    "like": article.like,
                    "date": article.date.strftime('%s'),
                    "retrieved_date": article.retrieved_date.strftime('%s')}
                    for article in feed.articles]})

    return jsonify(result=result)
