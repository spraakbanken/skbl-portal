# -*- coding: utf-8 -*
import os
import os.path
import json
import logging
import urllib
import shutil
import sys

from flask import Flask, g, request, redirect, render_template, url_for
from flask_babel import Babel
from setuptools import setup
from urllib2 import Request, urlopen
import HTMLParser
import helpers


app = Flask(__name__)

if os.path.exists(app.config.root_path + '/config.cfg') is False:
    print "copy config.default.cfg to config.cfg and add your settings"
    app.config.from_pyfile(app.config.root_path + '/config.default.cfg')
else:
    app.config.from_pyfile(app.config.root_path + '/config.cfg')


babel = Babel(app)


@babel.localeselector
def get_locale():
    locale = request.path[1:].split('/', 1)[0]

    if locale in ['sv', 'en']:
        return locale
    else:
        locale = 'sv'

        for lang in request.accept_languages.values():
            if lang[:2] in ['sv', 'en']:
                locale = lang[:2]
                break

        g.locale = locale
        return locale


def serve_static_page(page, title=''):
    set_language_switch_link(page)

    with app.open_resource("static/pages/%s/%s.html" % (page, g.language)) as f:
        data = f.read()

    return render_template('page_static.html',
                           content=data.decode('utf-8'),
                           title=title)


def set_language_switch_link(route, fragment=None, lang=''):
    if not lang:
        lang = get_locale()
    if lang == 'en':
        g.switch_language = {'url': url_for(route + '_sv'), 'label': 'Svenska'}
    else:
        g.switch_language = {'url': url_for(route + '_en'), 'label': 'English'}
    if fragment is not None:
        g.switch_language['url'] += '/' + fragment


def karp_query(action, query, mode='skbl'):
    query['mode'] = mode
    query['resource'] = 'skbl'
    query['size'] = app.config['RESULT_SIZE']
    params = urllib.urlencode(query)
    return karp_request("%s?%s" % (action, params))


def karp_request(action):
    q = Request("%s/%s" % (app.config['KARP_BACKEND'], action))
    # sys.stderr.write("\nREQUEST: %s/%s\n\n" % (app.config['KARP_BACKEND'], action))
    q.add_header('Authorization', "Basic %s" % (app.config['KARP_AUTH_HASH']))
    response = urlopen(q).read()
    logging.debug(q)
    data = json.loads(response)
    return data


@app.before_request
def func():
    g.babel = Babel
    g.language = get_locale()
    g.config = app.config


@app.context_processor
def inject_custom():
    d = {'lurl_for': lambda ep, **kwargs: url_for(ep + '_' + g.language, **kwargs)}
    return d

app.jinja_env.globals.update(get_first_name=helpers.get_first_name)
app.jinja_env.globals.update(get_life_range=helpers.get_life_range)
app.jinja_env.globals.update(make_namelist=helpers.make_namelist)
app.jinja_env.globals.update(make_placelist=helpers.make_placelist)
app.jinja_env.globals.update(make_placenames=helpers.make_placenames)
app.jinja_env.globals.update(make_alphabetical_bucket=helpers.make_alphabetical_bucket)
app.jinja_env.globals.update(get_date=helpers.get_date)
app.jinja_env.globals.update(join_name=helpers.join_name)
app.jinja_env.globals.update(sorted=sorted)
app.jinja_env.globals.update(len=len)
app.jinja_env.globals.update(get_lang_text=helpers.get_lang_text)


@app.template_filter('deescape')
def deescape_filter(s):
    # return s.replace("&amp;", "&").replace("&apos;", "'").replace("&quot;", '"')
    html_parser = HTMLParser.HTMLParser()
    return html_parser.unescape(s)


from app import views

if __name__ == '__main__':
    if sys.version_info.major < 3:
        reload(sys)
    sys.setdefaultencoding('utf8')
    app.run()
