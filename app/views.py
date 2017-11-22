# -*- coding=utf-8 -*-
import os
import os.path
from app import app, redirect, render_template, request, get_locale, set_language_switch_link, g, serve_static_page, karp_query
import computeviews
from flask import jsonify, url_for
from flask_babel import gettext
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
import helpers
from pylibmc import Client
import re
import smtplib

client = Client(app.config['MEMCACHED'])


# redirect to specific language landing-page
@app.route('/')
def index():
    return redirect('/' + get_locale())


@app.route('/en', endpoint='index_en')
@app.route('/sv', endpoint='index_sv')
def start():
    rule = request.url_rule
    if 'sv' in rule.rule:
        infotext = u"""<p>Läs om 1 000 svenska kvinnor från medeltid till nutid.</p>
                       <p>Genom olika sökningar kan du se vad de arbetade med,
                       vilken utbildning de fick, vilka organisationer de var med i,
                       hur de rörde sig i världen, vad de åstadkom och mycket mera.</p>
                       <p>Alla har de bidragit till samhällets utveckling.</p>"""
    else:
        infotext = u"""<p>Read up on 1000 Swedish women – from the middle ages to the present day.</p>
                       <p>Use the search function to reveal what these women got up to, how they were educated,
                       which organisations they belonged to, whether they travelled, what they achieved, and much more.</p>
                       <p>All of them contributed in a significant way to the development of Swedish society.</p>"""
    set_language_switch_link("index")
    return render_template('start.html', infotext=infotext)


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


@app.route('/en/contact/', methods=['POST'], endpoint="submitted_en")
@app.route('/sv/kontakt/', methods=['POST'], endpoint="submitted_sv")
def submit_contact_form():
    set_language_switch_link("contact")
    name = request.form['name'].strip()
    email = request.form['email'].strip()
    message = request.form['message']

    errors = []
    if not name or not email or not message:
        errors.append(gettext("Please enter all the fields!"))
    if email and not helpers.is_email_address_valid(email):
        errors.append(gettext("Please enter a valid email address!"))

    # Render error messages and tell user what went wrong
    if errors:
        name_error = False if name else True
        email_error = False if email else True
        message_error = False if message else True
        return render_template("contact.html",
                               title=gettext("Contact"),
                               headline=gettext("Contact SKBL"),
                               errors=errors,
                               name_error=name_error,
                               email_error=email_error,
                               message_error=message_error,
                               name=name,
                               email=email,
                               message=message)

    # Compose and send email
    else:
        text = u"%s har skickat följande meddelande:\n\n%s" % (name, message)
        html = text.replace("\n", "<br>")
        part1 = MIMEText(text, "plain", "utf-8")
        part2 = MIMEText(html, "html", "utf-8")

        msg = MIMEMultipart("alternative")
        msg.attach(part1)
        msg.attach(part2)

        msg["Subject"] = u"Förfrågan från skbl.se"
        msg['To'] = app.config['EMAIL_RECIPIENT']

        # Work-around: things won't be as pretty if email adress contains non-ascii chars
        if helpers.is_ascii(email):
            msg['From'] = "%s <%s>" % (Header(name, 'utf-8'), email)
        else:
            msg['From'] = u"%s <%s>" % (name, email)
            email = ""

        server = smtplib.SMTP("localhost")
        server.sendmail(email, [app.config['EMAIL_RECIPIENT']], msg.as_string())
        server.quit()

        # Render user feedback
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
        # karp_q['sort'] = '_score'
    else:
        karp_q['q'] = "extended||and|anything|contains|%s" % search

    data = karp_query('query', karp_q, mode='skbllinks')
    advanced_search_text = ''
    with app.open_resource("static/pages/advanced-search/%s.html" % (g.language)) as f:
        advanced_search_text = f.read()

    return render_template('list.html', headline="", subheadline=gettext('Hits for "%s"') % search.decode("UTF-8"),
                           hits=data["hits"],
                           advanced_search_text=advanced_search_text.decode("UTF-8"),
                           search=search.decode("UTF-8"),
                           alphabetic=True)


@app.route("/en/place", endpoint="place_index_en")
@app.route("/sv/ort", endpoint="place_index_sv")
def place_index():
    return computeviews.compute_place(client)


@app.route("/en/place/<place>", endpoint="place_en")
@app.route("/sv/ort/<place>", endpoint="place_sv")
def place(place=None):
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    set_language_switch_link("place_index", place)
    hits = karp_query('querycount', {'q': "extended||and|plats.search|equals|%s" % (place.encode('utf-8'))})
    if hits['query']['hits']['total'] > 0:
        return render_template('placelist.html', title=place, lat=lat, lon=lon,
                               headline=place, hits=hits["query"]["hits"])
    else:
        return render_template('page.html', content='not found')


@app.route("/en/organisation", endpoint="organisation_index_en")
@app.route("/sv/organisation", endpoint="organisation_index_sv")
def organisation_index():
    return computeviews.compute_organisation(client)


@app.route("/en/organisation/<result>", endpoint="organisation_en")
@app.route("/sv/organisation/<result>", endpoint="organisation_sv")
def organisation(result=None):
    title = request.args.get('title')
    return searchresult(result, 'organisation', 'id', 'organisations', title=title)


@app.route("/en/activity", endpoint="activity_index_en")
@app.route("/sv/verksamhet", endpoint="activity_index_sv")
def activity_index():
    return computeviews.compute_activity(client)


@app.route("/en/activity/<result>", endpoint="activity_en")
@app.route("/sv/verksamhet/<result>", endpoint="activity_sv")
def activity(result=None):
    return searchresult(result, name='activity', searchfield='verksamhetstext',
                        imagefolder='activities', title=result)


@app.route("/en/keyword", endpoint="keyword_index_en")
@app.route("/sv/nyckelord", endpoint="keyword_index_sv")
def keyword_index():
    rule = request.url_rule
    if 'sv' in rule.rule:
        infotext = u"""Här finns en lista över de nyckelord som karakteriserar materialet.
        De handlar om tid, yrken, ideologier och mycket mera.
        Om du klickar på något av nyckelorden kan du se vilka kvinnor som kan karakteriseras med det."""
    else:
        infotext = u"""This generates a list of keywords which typically appear in the entries.
        These include time periods, occupations, ideologies and much more.
        Selecting a keyword generates a list of all the women who fall under the given category."""
    set_language_switch_link("keyword_index")
    return computeviews.bucketcall(queryfield='nyckelord', name='keyword', title='Keywords',
                                   infotext=infotext, alphabetical=True)


@app.route("/en/keyword/<result>", endpoint="keyword_en")
@app.route("/sv/nyckelord/<result>", endpoint="keyword_sv")
def keyword(result=None):
    return searchresult(result, 'keyword', 'nyckelord', 'keywords')


@app.route("/en/articleauthor", endpoint="articleauthor_index_en")
@app.route("/sv/artikelforfattare", endpoint="articleauthor_index_sv")
def authors():
    rule = request.url_rule
    if 'sv' in rule.rule:
        infotext = u"""Här förtecknas de personer som har bidragit med artiklar till Svenskt kvinnobiografiskt lexikon. """
    else:
        infotext = u"""This is a list of the authors who supplied articles to SKBL."""
    set_language_switch_link("articleauthor_index")
    return computeviews.bucketcall(queryfield='artikel_forfattare_fornamn.bucket,artikel_forfattare_efternamn',
                                   name='articleauthor', title='Article authors', sortby=lambda x: x[1],
                                   lastnamefirst=True, infotext=infotext, alphabetical=True)


@app.route("/en/articleauthor/<result>", endpoint="articleauthor_en")
@app.route("/sv/artikelforfattare/<result>", endpoint="articleauthor_sv")
def author(result=None):
    return searchresult(result, name='articleauthor',
                        searchfield='artikel_forfattare_fulltnamn',
                        imagefolder='authors', searchtype='contains')


def searchresult(result, name='', searchfield='', imagefolder='', searchtype='equals', title=''):
    qresult = result
    try:
        set_language_switch_link("%s_index" % name, result)
        qresult = result.encode('utf-8')
        hits = karp_query('querycount', {'q': "extended||and|%s.search|%s|%s" % (searchfield, searchtype, qresult)})
        title = title or result

        if hits['query']['hits']['total'] > 0:
            picture = None
            if os.path.exists(app.config.root_path + '/static/images/%s/%s.jpg' % (imagefolder, qresult)):
                picture = '/static/images/%s/%s.jpg' % (imagefolder, qresult)

            return render_template('list.html', picture=picture, alphabetic=True,
                                   title=title, headline=title, hits=hits["query"]["hits"])
        else:
            return render_template('page.html', content='not found')
    except Exception:
        return render_template('page.html', content="%s: extended||and|%s.search|%s|%s" % (app.config['KARP_BACKEND'], searchfield, searchtype, qresult))


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
        search = search.encode("UTF-8")
        data, id = find_link(search)
        if id:
            # only one hit is found, redirect to that page
            return redirect(url_for('article_' + g.language, id=id))
        elif data["query"]["hits"]["total"] > 1:
            # more than one hit is found, redirect to a listing
            return redirect(url_for('search_' + g.language, q=search))
        else:
            # no hits are found redirect to a 'not found' page
            return render_template('page.html', content='not found')

    art = computeviews.compute_article(client)
    return art


@app.route("/en/article/<id>", endpoint="article_en")
@app.route("/sv/artikel/<id>", endpoint="article_sv")
def article(id=None):
    try:
        data = karp_query('querycount', {'q': "extended||and|id.search|equals|%s" % (id)})
        set_language_switch_link("article_index", id)
        return show_article(data)
    except Exception as e:
        import sys
        print >> sys.stderr, e
        raise


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
        source = data['query']['hits']['hits'][0]['_source']
        source['es_id'] = data['query']['hits']['hits'][0]['_id']
        firstname, calling = helpers.get_first_name(source)
        # Print html for the names with the calling name and last name in bold
        formatted_names = [name if name != calling else "<b>" + name + "</b>" for name in firstname.split(" ")]
        source['showname'] = "%s <b>%s</b>" % (" ".join(formatted_names), source['name'].get('lastname', ''))
        if source.get('text'):
            source['text'] = helpers.markdown_html(helpers.mk_links(source['text']))
        # Extract linked names from source
        source['linked_names'] = find_linked_names(source.get("othernames", {}), source.get("showname"))
        source['othernames'] = helpers.group_by_type(source.get('othernames', {}), 'name')
        source['othernames'].append({'type': u'Förnamn', 'name': firstname})
        helpers.collapse_kids(source)
        if "source" in source:
            source['source'] = helpers.aggregate_by_type(source['source'], use_markdown=True)
        if "furtherreference" in source:
            source['furtherreference'] = helpers.aggregate_by_type(source['furtherreference'], use_markdown=True)
        if type(source["article_author"]) != list:
            source["article_author"] = [source["article_author"]]
        # if "article_author" in source and type(source["article_author"] != list):
        #     source["article_author"] = [str(type(source["article_author"]))]#[source["article_author"]]
        return render_template('article.html', article=source, article_id=id)
    else:
        return render_template('page.html', content='not found')


def find_linked_names(othernames, showname):
    """Find and format linked names."""
    linked_names = []
    for item in othernames:
        if item.get("mk_link") is True:
            name = fix_name_order(item.get("name"))
            # Do not add linked name if all of its parts occur in showname
            if any(i for i in name.split() if i not in showname):
                linked_names.append(name)
    return ", ".join(linked_names)


def fix_name_order(name):
    """Lastname, Firstname --> Firstname Lastname"""
    nameparts = name.split(", ")
    if len(nameparts) == 1:
        return nameparts[0]
    elif len(nameparts) == 2:
        return nameparts[1] + " " + nameparts[0]
    elif len(nameparts) == 3:
        return nameparts[2] + " " + nameparts[1] + " " + nameparts[0]

# @app.route("/en/article-find/<id>", endpoint="article_en")
# @app.route("/sv/artikel-find/<id>", endpoint="article_sv")
# def article(link=None):
#     if re.match('[0-9 ]', link):
#         data = karp_query('querycount', {'q': "extended||and|swoid.search|equals|%s" % (link)})
#         set_language_switch_link("article_index", link)
#         show_article(data)


@app.route("/en/award", endpoint="award_index_en")
@app.route("/sv/pris", endpoint="award_index_sv")
def award_index():
    # There are no links to this page, but might be wanted later on
    # Exists only to support award/<result> below
    set_language_switch_link("award_index")
    return computeviews.bucketcall(queryfield='prisbeskrivning', name='award',
                                   title='Award', infotext='')


@app.route("/en/award/<result>", endpoint="award_en")
@app.route("/sv/pris/<result>", endpoint="award_sv")
def award(result=None):
    return searchresult(result, name='award',
                        searchfield='prisbeskrivning',
                        imagefolder='award', searchtype='equals')


@app.route("/en/article/<id>.json", endpoint="article_json_en")
@app.route("/sv/artikel/<id>.json", endpoint="article_json_sv")
def article_json(id=None):
    data = karp_query('querycount', {'q': "extended||and|id.search|equals|%s" % (id)})
    if data['query']['hits']['total'] == 1:
        return jsonify(data['query']['hits']['hits'][0]['_source'])


### Cache handling ###
@app.route('/emptycache')
def emptycache():
    # Users with write premissions to skbl may empty the cache
    emptied = False
    try:
        emptied = computeviews.compute_emptycache(client)
    except Exception as e:
        emptied = False
        # return jsonify({"error": "%s" % e})
    return jsonify({"cached_emptied": emptied})


@app.route('/cachestats')
def cachestats():
    return jsonify({"cached_stats": client.get_stats()})


@app.route("/en/fillcache", endpoint="fillcache_en")
@app.route("/sv/fillcache", endpoint="fillcache_sv")
def fillcache():
    # Refill the cache (~ touch all pages)
    # This request will take some seconds, users may want to make an
    # asynchronous call
    # for lang in ["sv", "en"]:
    computeviews.compute_article(client)
    computeviews.compute_activity(client)
    computeviews.compute_organisation(client)
    computeviews.compute_place(client)
    lang = 'sv' if 'sv' in request.url_rule.rule else 'en'
    return jsonify({"cache_filled": True, "cached_language": lang})


#     from threading import Thread
#     cachedpages = [computeviews.compute_article, computeviews.compute_activity,
#                    computeviews.compute_organisation, computeviews.compute_place]
#     for page in cachedpages:
#         t = Thread(target=page, args=[client])
#         t.daemon = True
#         t.start()
