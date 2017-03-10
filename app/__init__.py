# coding: utf-8
import os
import os.path
import json
import urllib
import shutil

from flask import Flask, g, request, redirect, render_template, url_for
from flask_babel import Babel
from setuptools import setup
from urllib2 import Request, urlopen 


app = Flask(__name__)

if os.path.exists('config.cfg') == False:
    print "copy config.default.cfg to config.cfg and add your config settings"
    app.config.from_pyfile('../config.default.cfg')
else:
    app.config.from_pyfile('../config.cfg')
    
    
babel = Babel(app)


@babel.localeselector
def get_locale():
    lang = request.path[1:].split('/', 1)[0]
    user = getattr(g, 'user', None)
    if lang in ['sv', 'en']:
        return lang
    elif user is not None:
        return user.locale
    else:
        return request.accept_languages.best_match(['sv', 'en'])


def serve_static_page(page, title=''):
    set_language_swith_link(page)
    
    with app.open_resource("static/pages/%s/%s.html" % (page, g.language)) as f:
        data = f.read()
    
    return render_template('page_static.html', 
                            content = data.decode('utf-8'), 
                            title = title)


def set_language_swith_link(route, fragment=None):
    if(get_locale() == 'en'):
        g.switch_language = {'url': url_for(route+'_sv'), 'label': 'Svenska'}
    else:
        g.switch_language = {'url': url_for(route+'_en'), 'label': 'English'}
    if(fragment != None):
        g.switch_language['url'] += '/'+fragment


def karp_query(query):
    params = urllib.urlencode({
                                'mode':'skbl',
                                'resource':'skbl',
                                'q': query
                              })
    return karp_request("querycount?%s" % (params))


def karp_request(action):
    q = Request("%s/%s" % (app.config['KARP_BACKEND'], action))
    print "%s/%s" % (app.config['KARP_BACKEND'], action)
    q.add_header('Authorization', "Basic %s" % (app.config['KARP_AUTH_HASH']))
    response = urlopen(q).read()
    data = json.loads(response)
    return data

@app.before_request
def func():
    g.babel = Babel
    g.language = get_locale()


@app.context_processor
def inject_custom():
    d = {'lurl_for': lambda ep, **kwargs: url_for(ep+'_'+g.language, **kwargs)}
    return d


from app import views

if __name__ == '__main__':
    app.run()
