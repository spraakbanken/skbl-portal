# -*- coding=utf-8 -*-
import os
import os.path
import re
from app import app, redirect, render_template, request, get_locale, set_language_swith_link, g, serve_static_page, karp_query, karp_request
from flask_babel import gettext
import helpers
import logging
from urllib2 import Request, urlopen
from flask import Markup

log = logging.getLogger(__name__)

#redirect to specific language landing-page
@app.route('/')
def index():
    return redirect('/'+get_locale())


@app.route('/en', endpoint='index_en')
@app.route('/sv', endpoint='index_sv')
def start():
    set_language_swith_link("index")
    return render_template('start.html')


@app.route("/en/about-skbl", endpoint="about-skbl_en")
@app.route("/sv/om-skbl", endpoint="about-skbl_sv")
def about_skbl():
    return serve_static_page("about-skbl", gettext("About SKBL"))


@app.route("/en/about-us", endpoint="about-us_en")
@app.route("/sv/om-oss", endpoint="about-us_sv")
def about_us():
    return serve_static_page("about-us", gettext("About us"))


@app.route("/en/contact", endpoint="contact_en")
@app.route("/sv/kontakt", endpoint="contact_sv")
def contact():
    return serve_static_page("contact", gettext("Contact"))


@app.route("/en/search", endpoint="search_en")
@app.route("/sv/sok", endpoint="search_sv")
def search():
    set_language_swith_link("search")
    data = karp_query('querycount', {'q' : "extended||and|anything.search|equals|%s" % (request.args.get('q', '*'))})
    return render_template('search.html', hits = data["query"]["hits"])


    advanced_search_text = ''
    with app.open_resource("static/pages/advanced-search/%s.html" % (g.language)) as f:
        advanced_search_text = f.read()

    return render_template('search.html', hits = data["query"]["hits"], advanced_search_text=advanced_search_text)

@app.route("/en/advanced-search", endpoint="search_advanced_en")
@app.route("/sv/avncerad-sok", endpoint="search_advanced_sv")
def search_advanced():
    return serve_static_page("advanced-search", gettext("Advanced search"))

@app.route("/en/places", endpoint="places_index_en")
@app.route("/sv/orter", endpoint="places_index_sv")
def places_index():
    def parse(kw):
        place = kw.get('key')
        name, lat, lon = place.split('|')
        placename = name if name else '%s, %s' % (lat,lon)
        lat = place.split('|')[1]
        lon = place.split('|')[2]
        return {'name': placename, 'lat': lat, 'lon': lon,
                'count': kw.get('doc_count')}

    data = karp_query('getplaces', {})
    stat_table = [parse(kw) for kw in data['places']]
    stat_table.sort()
    set_language_swith_link("places_index")
    return render_template('places.html', places=stat_table, title=gettext("Places"))


@app.route("/en/place/<place>", endpoint="place_en")
@app.route("/sv/ort/<place>", endpoint="place_sv")
def place(place=None):
    place = place.encode('utf-8')
    set_language_swith_link("places_index", place)
    hits = karp_query('querycount', {'q' : "extended||and|plats.search|equals|%s" % (place)})

    if hits['query']['hits']['total'] > 0:
        return render_template('keyword.html', title=place, hits=hits["query"]["hits"], picture=None)
    else:
        return render_template('page.html', content = 'not found')


@app.route("/en/keyword", endpoint="keyword_index_en")
@app.route("/sv/nyckelord", endpoint="keyword_index_sv")
def keyword_index():
    data = karp_query('statlist', {'buckets' : 'nyckelord.bucket'})
    stat_table = [kw for kw in data['stat_table'] if kw[0] != ""]
    stat_table.sort()
    set_language_swith_link("keyword_index")
    return render_template('keywords.html', keywords=stat_table, title=gettext("Keywords"))


@app.route("/en/keyword/<keyword>", endpoint="keyword_en")
@app.route("/sv/nyckelord/<keyword>", endpoint="keyword_sv")
def keyword(keyword=None):
    keyword = keyword.encode('utf-8')
    set_language_swith_link("keyword_index", keyword)
    hits = karp_query('querycount', {'q' : "extended||and|nyckelord.search|equals|%s" % (keyword)})

    if hits['query']['hits']['total'] > 0:
        picture = None
        if os.path.exists(app.config.root_path+'/static/images/keywords/'+keyword+'.jpg'):
            picture = keyword+'.jpg'

        return render_template('keyword.html', picture=picture, title=keyword, hits=hits["query"]["hits"])
    else:
        return render_template('page.html', content = 'not found')


@app.route("/en/article", endpoint="article_index_en")
@app.route("/sv/artikel", endpoint="article_index_sv")
def article_index():
    print('katt')
    set_language_swith_link("article_index")
    data = karp_query('query', {'q':"extended||and|namn.search|exists"})
    return render_template('list.html',
                            hits = data["hits"],
                            headline="Women A-Ö",
                            title = 'Articles')


@app.route("/en/article/<id>", endpoint="article_en")
@app.route("/sv/artikel/<id>", endpoint="article_sv")
def article(id=None):
    data = karp_query('querycount', {'q' : "extended||and|id.search|equals|%s" % (id)})
    set_language_swith_link("article_index", id)
    if data['query']['hits']['total'] == 1:
        # Malin: visa bara tilltalsnamnet (obs test, kanske inte är vad de vill ha på riktigt)
        source = data['query']['hits']['hits'][0]['_source']
        firstname, calling = helpers.get_first_name(source)
        # Print given name + lastname
        source['showname'] = "%s %s" % (calling, source['name'].get('lastname', ''))
        # If there are additional names (mellannamn), print the full first name
        # if calling != firstname:
        #     source['fullfirstname'] = firstname
        # Malin, test: transalte ** to emphasis
        source['text'] = helpers.markdown_html(source['text'])
        source['othernames'] = helpers.group_by_type(source.get('othernames', {}), 'name')
        source['othernames'].append({'type': u'Förnamn', 'name': firstname})
        return render_template('article.html', article = source)
    else:
        return render_template('page.html', content = 'not found')
