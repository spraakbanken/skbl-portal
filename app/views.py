# -*- coding=utf-8 -*-
import os
import os.path
from app import app, send_mail, redirect, render_template, request, get_locale, set_language_switch_link, g, serve_static_page, karp_query
from collections import defaultdict
from flask import jsonify, url_for
from flask_babel import gettext
from flask_sendmail import Message
import icu  # pip install PyICU
import helpers
import re
import sys


# redirect to specific language landing-page
@app.route('/')
def index():
    return redirect('/' + get_locale())


@app.route('/en', endpoint='index_en')
@app.route('/sv', endpoint='index_sv')
def start():
    set_language_switch_link("index")
    return render_template('start.html')


@app.route("/en/about-skbl", endpoint="about-skbl_en")
@app.route("/sv/om-skbl", endpoint="about-skbl_sv")
def about_skbl():
    return serve_static_page("about-skbl", gettext("About SKBL"))


@app.route("/en/contact", endpoint="contact_en")
@app.route("/sv/kontakt", endpoint="contact_sv")
def contact():
    set_language_switch_link("contact")
    return render_template("contact.html",
                           title=gettext("Contact"),
                           headline=gettext("Contact SKBL"))


@app.route('/en/submitted/', methods=['POST'])
@app.route('/sv/submitted/', methods=['POST'])
def submit_contact_form():
    set_language_switch_link("index")
    name = request.form['name']
    email = request.form['email']
    message = request.form['message']
    body = name + u" har skickat följande meddelande:\n\n" + message

    msg = Message(subject=u"Förfrågan från skbl.se",
                  body=body.encode("UTF-8"),
                  sender=email,
                  recipients=[app.config['EMAIL_RECIPIENT']]
                  )

    send_mail(msg)

    return render_template("form_submitted.html",
                           title=gettext("Thank you for your feedback") + "!",
                           headline=gettext("Thank you for your feedback") + ", " + name + "!",
                           text=gettext("We will get back to you as soon as we can."))


@app.route("/en/search", endpoint="search_en")
@app.route("/sv/sok", endpoint="search_sv")
def search():
    set_language_switch_link("search")
    search = request.args.get('q', '*').encode('utf-8')
    karp_q = {}
    if '*' in search:
        search = re.sub('(?<!\.)\*', '.*', search)
        karp_q['q'] = "extended||and|anything|regexp|%s" % search
        karp_q['sort'] = '_score'
    else:
        karp_q['q'] = "simple||%s" % search

    data = karp_query('querycount', karp_q)
    advanced_search_text = ''
    with app.open_resource("static/pages/advanced-search/%s.html" % (g.language)) as f:
        advanced_search_text = f.read()

    return render_template('list.html', headline=gettext('Search'),
                           hits=data["query"]["hits"],
                           advanced_search_text=advanced_search_text.decode("UTF-8"),
                           alphabetic=False)


@app.route("/en/place", endpoint="place_index_en")
@app.route("/sv/ort", endpoint="place_index_sv")
def place_index():
    set_language_switch_link("place_index")

    def parse(kw):
        place = kw.get('key')
        name, lat, lon = place.split('|')
        placename = name if name else '%s, %s' % (lat, lon)
        lat = place.split('|')[1]
        lon = place.split('|')[2]
        return {'name': placename, 'lat': lat, 'lon': lon,
                'count': kw.get('doc_count')}

    def has_name(kw):
        return kw.get('key').split('|')[0]

    data = karp_query('getplaces', {})
    stat_table = [parse(kw) for kw in data['places'] if has_name(kw)]
    # Sort and translate
    # stat_table = helpers.sort_places(stat_table, request.url_rule)
    collator = icu.Collator.createInstance(icu.Locale('sv_SE.UTF-8'))
    stat_table.sort(key=lambda x: collator.getSortKey(x.get('name').strip()))

    return render_template('places.html', places=stat_table, title=gettext("Places"))


@app.route("/en/place/<place>", endpoint="place_en")
@app.route("/sv/ort/<place>", endpoint="place_sv")
def place(place=None):
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    set_language_switch_link("place_index", place)
    hits = karp_query('querycount', {'q': "extended||and|plats.search|equals|%s" % (place.encode('utf-8'))})
    if hits['query']['hits']['total'] > 0:
        return render_template('placelist.html', title=place, lat=lat, lon=lon, headline=place, hits=hits["query"]["hits"])
    else:
        return render_template('page.html', content='not found')


@app.route("/en/organisation", endpoint="organisation_index_en")
@app.route("/sv/organisation", endpoint="organisation_index_sv")
def organisation_index():
    infotext = u"""De organisationer där kvinnor varit aktiva finns sorterade ämnesvis
    (politik, religion, idrott, ideell m fl.). Välj ämne för att se organisationer
    inom detta och vilka kvinnor som var aktiva i dem."""
    data = karp_query('minientry', {'q': 'extended||and|anything|regexp|.*',
                                    'show': 'organisationsnamn,organisationstyp'})
    set_language_switch_link("organisation_index")
    nested_obj = {}
    for hit in data['hits']['hits']:
        for org in hit['_source'].get('organisation', []):
            orgtype = org.get('type', '-')
            if orgtype not in nested_obj:
                nested_obj[orgtype] = defaultdict(set)
            nested_obj[orgtype][org.get('name', '-')].add(hit['_id'])
    return render_template('nestedbucketresults.html',
                           results=nested_obj, title=gettext("Organizations"),
                           infotext=infotext, name='organisation')
    # return bucketcall(queryfield='organisationstyp', name='organisation',
    #                   title='Organizations', infotext=infotext)


@app.route("/en/organisation/<result>", endpoint="organisation_en")
@app.route("/sv/organisation/<result>", endpoint="organisation_sv")
def organisation(result=None):
    title = request.args.get('title')
    return searchresult(result, 'organisation', 'id', 'organisations', title=title)


@app.route("/en/activity", endpoint="activity_index_en")
@app.route("/sv/verksamhet", endpoint="activity_index_sv")
def activity_index():
    infotext = u"Här listas kvinnornas yrken och andra verksamheter."
    return bucketcall(queryfield='verksamhetstext', name='activity',
                      title='Activities', infotext=infotext)


@app.route("/en/activity/<result>", endpoint="activity_en")
@app.route("/sv/verksameht/<result>", endpoint="activity_sv")
def activity(result=None):
    return searchresult(result, 'activity', 'verksamhetstext', 'activities')


@app.route("/en/keyword", endpoint="keyword_index_en")
@app.route("/sv/nyckelord", endpoint="keyword_index_sv")
def keyword_index():
    infotext = u"""Nyckelorden (ämnesorden) sammanfattar kvinnornas verksamheter,
    utan att specificera dem, t ex. Kvinnorörelsen, Fredsrörelsen, Konstnärer etc.
    Klicka på ett nyckelord för att få en lista på biografier där det används."""
    return bucketcall(queryfield='nyckelord', name='keyword', title='Keywords', infotext=infotext)


@app.route("/en/keyword/<result>", endpoint="keyword_en")
@app.route("/sv/nyckelord/<result>", endpoint="keyword_sv")
def keyword(result=None):
    return searchresult(result, 'keyword', 'nyckelord', 'keywords')


@app.route("/en/articleauthor", endpoint="articleauthor_index_en")
@app.route("/sv/artikelforfattare", endpoint="articleauthor_index_sv")
def authors():
    infotext = u"Klicka på författarens namn för att komma till en kortfattad författarinformation."
    return bucketcall(queryfield='artikel_forfattare_fornamn.bucket,artikel_forfattare_efternamn',
                      name='articleauthor', title='Article authors', sortby=lambda x: x[1], lastnamefirst=True, infotext=infotext)


@app.route("/en/articleauthor/<result>", endpoint="articleauthor_en")
@app.route("/sv/artikelforfattare/<result>", endpoint="articleauthor_sv")
def author(result=None):
    return searchresult(result, name='articleauthor', searchfield='artikel_forfattare_fulltnamn',
                        imagefolder='authors', searchtype='contains')


def searchresult(result, name='', searchfield='', imagefolder='', searchtype='equals', title=''):
    try:
        set_language_switch_link("%s_index" % name, result)
        qresult = result.encode('utf-8')
        hits = karp_query('querycount', {'q': "extended||and|%s.search|%s|%s" % (searchfield, searchtype, qresult)})
        title = title or result

        if hits['query']['hits']['total'] > 0:
            picture = None
            if os.path.exists(app.config.root_path + '/static/images/%s/%s.jpg' % (imagefolder, qresult)):
                picture = '/static/images/%s/%s.jpg' % (imagefolder, qresult)

            return render_template('list.html', picture=picture, alphabetic=True, title=title, headline=title, hits=hits["query"]["hits"])
        else:
            return render_template('page.html', content='not found')
    except Exception:
        return render_template('page.html', content="%s: extended||and|%s.search|%s|%s" % (app.config['KARP_BACKEND'], searchfield, searchtype, qresult))


def bucketcall(queryfield='', name='', title='', sortby='', lastnamefirst=False, infotext=''):
    data = karp_query('statlist', {'buckets': '%s.bucket' % queryfield})
    stat_table = [kw for kw in data['stat_table'] if kw[0] != ""]
    if sortby:
        stat_table.sort(key=sortby)
    else:
        stat_table.sort()
    if lastnamefirst:
        stat_table = [[kw[1] + ',', kw[0], kw[2]] for kw in stat_table]
    set_language_switch_link("%s_index" % name)
    return render_template('bucketresults.html', results=stat_table, title=gettext(title), name=name, infotext=infotext)


# def nestedbucketcall(queryfield=[], paths=[], name='', title='', sortby='', lastnamefirst=False):
#     data = karp_query('minientry', {'size': 1000,
#                                 'q': 'exentded||and|anything|regexp|.*',
#                                 'show': ','.join(queryfield)})
#     stat_table = data['aggregations']['q_statistics']
#     set_language_switch_link("%s_index" % name)
#     return render_template('nestedbucketresults.html', paths=paths,
#                            results=stat_table, title=gettext(title), name=name)


@app.route("/en/article", endpoint="article_index_en")
@app.route("/sv/artikel", endpoint="article_index_sv")
def article_index(search=None):
    # search is only used by links in article text
    set_language_switch_link("article_index")

    search = search or request.args.get('search')
    if search is not None:
        data, id = find_link(search)
        if id:
           # only one hit is found, redirect to that page
           return redirect(url_for('article_'+g.language, id=id))
        elif data["query"]["hits"]["total"] > 1:
           # more than one hit is found, redirect to a listing
           return redirect(url_for('search_'+g.language, q=search))
        else:
           # no hits are found redirect to a 'not found' page
           return render_template('page.html', content='not found')

    data = karp_query('query', {'q': "extended||and|namn.search|exists"})
    infotext = u"""Klicka på namnet för att läsa biografin om den kvinna du vill veta mer om."""
    return render_template('list.html',
                           hits=data["hits"],
                           headline=gettext(u'Women A-Ö'),
                           alphabetic=True,
                           split_letters=True,
                           infotext=infotext,
                           title='Articles')


@app.route("/en/article/<id>", endpoint="article_en")
@app.route("/sv/artikel/<id>", endpoint="article_sv")
def article(id=None):
    data = karp_query('querycount', {'q': "extended||and|id.search|equals|%s" % (id)})
    set_language_switch_link("article_index", id)
    return show_article(data)


def find_link(searchstring):
    # Finds an article based on ISNI or name
    if re.search('^[0-9 ]*$', searchstring):
        data = karp_query('querycount',
                          {'q': "extended||and|swoid.search|equals|%s" % (searchstring)})
    else:
        data = karp_query('querycount',
                          {'q': "extended||and|namn.search|contains|%s" % (searchstring)})
    # The expected case: only one hit is found
    if data['query']['hits']['total'] == 1:
        id = data['query']['hits']['hits'][0]['_id']
        return data, id
    # Otherwise just return the data
    else:
        return data, ''


def show_article(data):
    if data['query']['hits']['total'] == 1:
        # Malin: visa bara tilltalsnamnet (obs test, kanske inte är vad de vill ha på riktigt)
        source = data['query']['hits']['hits'][0]['_source']
        firstname, calling = helpers.get_first_name(source)
        # Print given name + lastname
        source['showname'] = "%s %s" % (calling, source['name'].get('lastname', ''))
        source['text'] = helpers.markdown_html(helpers.mk_links(source['text']))
        source['othernames'] = helpers.group_by_type(source.get('othernames', {}), 'name')
        source['othernames'].append({'type': u'Förnamn', 'name': firstname})
        helpers.collapse_kids(source)
        if "source" in source:
            source['source'] = helpers.aggregate_by_type(source['source'], use_markdown=True)
        if "furtherreference" in source:
            source['furtherreference'] = helpers.aggregate_by_type(source['furtherreference'], use_markdown=True)
        return render_template('article.html', article=source, article_id=id)
    else:
        return render_template('page.html', content='not found')


# @app.route("/en/article-find/<id>", endpoint="article_en")
# @app.route("/sv/artikel-find/<id>", endpoint="article_sv")
# def article(link=None):
#     if re.match('[0-9 ]', link):
#         data = karp_query('querycount', {'q': "extended||and|swoid.search|equals|%s" % (link)})
#         set_language_switch_link("article_index", link)
#         show_article(data)



@app.route("/en/article/<id>.json", endpoint="article_json_en")
@app.route("/sv/artikel/<id>.json", endpoint="article_json_sv")
def article_json(id=None):
    data = karp_query('querycount', {'q': "extended||and|id.search|equals|%s" % (id)})
    if data['query']['hits']['total'] == 1:
        return jsonify(data['query']['hits']['hits'][0]['_source'])
