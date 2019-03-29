# -*- coding: utf-8 -*
"""Initialise Flask application."""

import os
import sys
import urllib

from flask import Flask, g, make_response, request, render_template, url_for
from flask_babel import Babel
from flask_compress import Compress
import HTMLParser
import json
# from setuptools import setup
from pylibmc import Client, ClientPool
from urllib2 import Request, urlopen

import helpers


app = Flask(__name__)

if os.path.exists(app.config.root_path + '/config.cfg') is False:
    print("copy config.default.cfg to config.cfg and add your settings")
    app.config.from_pyfile(app.config.root_path + '/config.default.cfg')
else:
    app.config.from_pyfile(app.config.root_path + '/config.cfg')


babel = Babel(app)
Compress(app)

client = Client(app.config['MEMCACHED'])
mc_pool = ClientPool(client, app.config['POOL_SIZE'])


def cache_name(pagename, lang=''):
    """Get page from cache."""
    if not lang:
        lang = 'sv' if 'sv' in request.url_rule.rule else 'en'
    return '%s_%s' % (pagename, lang)


def check_cache(page, lang=''):
    """
    Check if page is in cache.

    If the cache should not be used, return None.
    """
    if app.config['TEST']:
        return None
    try:
        with mc_pool.reserve() as client:
            # Look for the page, return if found
            art = client.get(cache_name(page, lang))
            if art is not None:
                return art
    except Exception:
        # TODO what to do??
        pass

    # If nothing is found, return None
    return None


def set_cache(page, name='', lang='', no_hits=0):
    """
    Browser cache handling.

    Add header to the response.
    May also add the page to the memcache.
    """
    pagename = cache_name(name, lang='')
    if no_hits >= app.config['CACHE_HIT_LIMIT']:
        try:
            with mc_pool.reserve() as client:
                client.set(pagename, page, time=app.config['LOW_CACHE_TIME'])
        except Exception:
            # TODO what to do??
            pass
    r = make_response(page)
    r.headers.set('Cache-Control', "public, max-age=%s" % app.config['BROWSER_CACHE_TIME'])
    return r


@babel.localeselector
def get_locale():
    """Get correct language from url."""
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
    """Serve static html."""
    set_language_switch_link(page)
    with app.open_resource("static/pages/%s/%s.html" % (page, g.language)) as f:
        data = f.read()

    return render_template('page_static.html',
                           content=data.decode('utf-8'),
                           title=title)


def set_language_switch_link(route, fragment=None, lang=''):
    """Fix address and label for language switch button."""
    if not lang:
        lang = get_locale()
    if lang == 'en':
        g.switch_language = {'url': url_for(route + '_sv'), 'label': 'Svenska'}
    else:
        g.switch_language = {'url': url_for(route + '_en'), 'label': 'English'}
    if fragment is not None:
        g.switch_language['url'] += '/' + fragment


def karp_query(action, query, mode=app.config['KARP_MODE']):
    """Generate query and send request to Karp."""
    query['mode'] = mode
    query['resource'] = app.config['KARP_LEXICON']
    if 'size' not in query:
        query['size'] = app.config['RESULT_SIZE']
    params = urllib.urlencode(query)
    return karp_request("%s?%s" % (action, params))


def karp_request(action):
    """Send request to Karp backend."""
    q = Request("%s/%s" % (app.config['KARP_BACKEND'], action))
    if app.config['DEBUG']:
        sys.stderr.write("\nREQUEST: %s/%s\n\n" % (app.config['KARP_BACKEND'], action))
    q.add_header('Authorization', "Basic %s" % (app.config['KARP_AUTH_HASH']))
    response = urlopen(q).read()
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


@app.template_filter('deescape')
def deescape_filter(s):
    html_parser = HTMLParser.HTMLParser()
    return html_parser.unescape(s)


app.jinja_env.globals.update(get_life_range=helpers.get_life_range)
app.jinja_env.globals.update(make_namelist=helpers.make_namelist)
app.jinja_env.globals.update(make_simplenamelist=helpers.make_simplenamelist)
app.jinja_env.globals.update(make_placelist=helpers.make_placelist)
app.jinja_env.globals.update(make_placenames=helpers.make_placenames)
app.jinja_env.globals.update(make_alphabetical_bucket=helpers.make_alphabetical_bucket)
app.jinja_env.globals.update(make_alpha_more_women=helpers.make_alpha_more_women)
app.jinja_env.globals.update(get_date=helpers.get_date)
app.jinja_env.globals.update(join_name=helpers.join_name)
app.jinja_env.globals.update(sorted=sorted)
app.jinja_env.globals.update(len=len)
app.jinja_env.globals.update(get_lang_text=helpers.get_lang_text)
app.jinja_env.globals.update(get_shorttext=helpers.get_shorttext)
app.jinja_env.globals.update(get_org_name=helpers.get_org_name)
app.jinja_env.globals.update(rewrite_von=helpers.rewrite_von)
app.jinja_env.globals.update(lowersorted=helpers.lowersorted)
app.jinja_env.globals.update(get_current_date=helpers.get_current_date)


from app import views


if __name__ == '__main__':
    if sys.version_info.major < 3:
        reload(sys)
    sys.setdefaultencoding('utf8')
    app.run()
