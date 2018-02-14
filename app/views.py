# -*- coding=utf-8 -*-
import os
import os.path
from app import app, redirect, render_template, request, get_locale, set_language_switch_link, g, serve_static_page, karp_query, mc_pool, set_cache
import computeviews
from flask import jsonify, url_for
from flask_babel import gettext
import helpers
import re
import static_info
import icu  # pip install PyICU


# redirect to specific language landing-page
@app.route('/')
def index():
    return redirect('/' + get_locale())


@app.route('/en', endpoint='index_en')
@app.route('/sv', endpoint='index_sv')
def start():
    infotext = helpers.get_infotext("start", request.url_rule.rule)
    set_language_switch_link("index")
    page = render_template('start.html',
                           title="Svenskt kvinnobiografiskt lexikon",
                           infotext=infotext,
                           description=helpers.get_shorttext(infotext))
    return set_cache(page)


@app.route("/en/about-skbl", endpoint="about-skbl_en")
@app.route("/sv/om-skbl", endpoint="about-skbl_sv")
def about_skbl():
    page = serve_static_page("about-skbl", gettext("About SKBL"))
    return set_cache(page)


@app.route("/en/more-women", endpoint="more-women_en")
@app.route("/sv/fler-kvinnor", endpoint="more-women_sv")
def more_women():
    infotext = helpers.get_infotext("more-women", request.url_rule.rule)
    set_language_switch_link("more-women")
    page = render_template('more_women.html',
                           women=static_info.more_women,
                           infotext=infotext,
                           linked_from=request.args.get('linked_from'),
                           title=gettext("More women"))
    return set_cache(page)


@app.route("/en/biographies", endpoint="biographies_en")
@app.route("/sv/biografiska-verk", endpoint="biographies_sv")
def biographies():
    page = serve_static_page("biographies", gettext("Older biographies"))
    return set_cache(page)


@app.route("/en/contact", endpoint="contact_en")
@app.route("/sv/kontakt", endpoint="contact_sv")
def contact():
    set_language_switch_link("contact")

    # Set suggestion checkbox
    if request.args.get('suggest') == 'true':
        mode = "suggestion"
    else:
        mode = "other"
    page = render_template("contact.html",
                           title=gettext("Contact"),
                           headline=gettext("Contact SKBL"),
                           form_data={},
                           mode=mode)
    return set_cache(page)


@app.route('/en/contact/', methods=['POST'], endpoint="submitted_en")
@app.route('/sv/kontakt/', methods=['POST'], endpoint="submitted_sv")
def submit_contact_form():
    return computeviews.compute_contact_form()


@app.route("/en/search", endpoint="search_en")
@app.route("/sv/sok", endpoint="search_sv")
def search():
    set_language_switch_link("search")
    search = request.args.get('q', '*').encode('utf-8')
    show = ','.join(['name', 'url', 'undertitel', 'lifespan'])
    karp_q = {'highlight': True, 'size': app.config['SEARCH_RESULT_SIZE'],
              'show': show}
    if '*' in search:
        search = re.sub('(?<!\.)\*', '.*', search)
        karp_q['q'] = "extended||and|anything|regexp|%s" % search
        # karp_q['sort'] = '_score'
    else:
        karp_q['q'] = "extended||and|anything|contains|%s" % search

    data = karp_query('minientry', karp_q, mode='skbl')
    advanced_search_text = ''
    with app.open_resource("static/pages/advanced-search/%s.html" % (g.language)) as f:
        advanced_search_text = f.read()
    karp_url = "https://spraakbanken.gu.se/karp/#?mode=skbl&advanced=false&hpp=25&extended=and%7Cnamn%7Cequals%7C&searchTab=simple&page=1&search=simple%7C%7C" + search.decode("utf-8")

    t = render_template('list.html', headline="", subheadline=gettext('Hits for "%s"') % search.decode("UTF-8"),
                        hits_name=data["hits"],
                        hits=data["hits"],
                        advanced_search_text=advanced_search_text.decode("UTF-8"),
                        search=search.decode("UTF-8"),
                        alphabetic=True,
                        karp_url=karp_url,
                        more=data["hits"]["total"] > app.config["SEARCH_RESULT_SIZE"])

    return set_cache(t)


@app.route("/en/place", endpoint="place_index_en")
@app.route("/sv/ort", endpoint="place_index_sv")
def place_index():
    return computeviews.compute_place()


@app.route("/en/place/<place>", endpoint="place_en")
@app.route("/sv/ort/<place>", endpoint="place_sv")
def place(place=None):
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    set_language_switch_link("place_index", place)
    hits = karp_query('querycount', {'q': "extended||and|plats.search|equals|%s" % (place.encode('utf-8'))})
    if hits['query']['hits']['total'] > 0:
        page = render_template('placelist.html', title=place, lat=lat, lon=lon,
                               headline=place, hits=hits["query"]["hits"])
    else:
        page = render_template('page.html', content='not found')
    return set_cache(page)


@app.route("/en/organisation", endpoint="organisation_index_en")
@app.route("/sv/organisation", endpoint="organisation_index_sv")
def organisation_index():
    return computeviews.compute_organisation()


@app.route("/en/organisation/<result>", endpoint="organisation_en")
@app.route("/sv/organisation/<result>", endpoint="organisation_sv")
def organisation(result=None):
    title = request.args.get('title')
    page = searchresult(result, 'organisation', 'id', 'organisations', title=title)
    return set_cache(page)


@app.route("/en/activity", endpoint="activity_index_en")
@app.route("/sv/verksamhet", endpoint="activity_index_sv")
def activity_index():
    return computeviews.compute_activity()


@app.route("/en/activity/<result>", endpoint="activity_en")
@app.route("/sv/verksamhet/<result>", endpoint="activity_sv")
def activity(result=None):
    page = searchresult(result, name='activity', searchfield='verksamhetstext',
                        imagefolder='activities', title=result)
    return set_cache(page)


@app.route("/en/keyword", endpoint="keyword_index_en")
@app.route("/sv/nyckelord", endpoint="keyword_index_sv")
def keyword_index():
    infotext = helpers.get_infotext("keyword", request.url_rule.rule)
    set_language_switch_link("keyword_index")

    # Fix list with references to be inserted in results
    reference_list = static_info.keywords_reference_list
    [ref.append("reference") for ref in reference_list]

    return computeviews.bucketcall(queryfield='nyckelord', name='keyword',
                                   title='Keywords', infotext=infotext,
                                   alphabetical=True,
                                   insert_entries=reference_list,
                                   description=helpers.get_shorttext(infotext))


@app.route("/en/keyword/<result>", endpoint="keyword_en")
@app.route("/sv/nyckelord/<result>", endpoint="keyword_sv")
def keyword(result=None):
    page = searchresult(result, 'keyword', 'nyckelord', 'keywords')
    return set_cache(page)


@app.route("/en/articleauthor", endpoint="articleauthor_index_en")
@app.route("/sv/artikelforfattare", endpoint="articleauthor_index_sv")
def authors():
    infotext = helpers.get_infotext("articleauthor", request.url_rule.rule)
    set_language_switch_link("articleauthor_index")
    return computeviews.compute_artikelforfattare(infotext=infotext, description=helpers.get_shorttext(infotext))


@app.route("/en/articleauthor/<result>", endpoint="articleauthor_en")
@app.route("/sv/artikelforfattare/<result>", endpoint="articleauthor_sv")
def author(result=None):
    # rule = request.url_rule
    # lang = 'sv' if 'sv' in rule.rule else 'en'
    # Try to get authorinfo in correct language (with Swedish as fallback)
    # authorinfo = static_info.authorsdict.get(result)
    # if authorinfo:
    #     authorinfo = authorinfo.get(lang, authorinfo.get("sv"))
    authorinfo = False
    page = searchresult(result, name='articleauthor',
                        searchfield='artikel_forfattare_fulltnamn',
                        imagefolder='authors', searchtype='contains',
                        authorinfo=authorinfo)
    return set_cache(page)


def searchresult(result, name='', searchfield='', imagefolder='',
                 searchtype='equals', title='', authorinfo=False):
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
                                   title=title, headline=title, hits=hits["query"]["hits"], authorinfo=authorinfo)
        else:
            return render_template('page.html', content='not found')
    except Exception as e:
        return render_template('page.html', content="%s\n%s: extended||and|%s.search|%s|%s" % (e, app.config['KARP_BACKEND'], searchfield, searchtype, qresult))


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
            page = redirect(url_for('article_' + g.language, id=id))
            return set_cache(page)
        elif data["query"]["hits"]["total"] > 1:
            # more than one hit is found, redirect to a listing
            page = redirect(url_for('search_' + g.language, q=search))
            return set_cache(page)
        else:
            # no hits are found redirect to a 'not found' page
            return render_template('page.html', content='not found')

    art = computeviews.compute_article()
    return art


@app.route("/en/article/<id>", endpoint="article_en")
@app.route("/sv/artikel/<id>", endpoint="article_sv")
def article(id=None):
    rule = request.url_rule
    if 'sv' in rule.rule:
        lang = "sv"
    else:
        lang = "en"
    data = karp_query('querycount', {'q': "extended||and|url|equals|%s" % (id)})
    if data['query']['hits']['total'] == 0:
        data = karp_query('querycount', {'q': "extended||and|id.search|equals|%s" % (id)})
    set_language_switch_link("article_index", id)
    page = show_article(data, lang)
    return set_cache(page)


@app.route("/en/article/EmptyArticle", endpoint="article_empty_en")
@app.route("/sv/artikel/TomArtikel", endpoint="article_empty_sv")
def empty_article():
    set_language_switch_link("article_empty")
    rule = request.url_rule
    if 'sv' in rule.rule:
        content = u"""Den här kvinnan saknas än så länge."""
    else:
        content = u"""This entry does not exist yet."""
    page = render_template('page.html', content=content)
    return set_cache(page)


def find_link(searchstring):
    # Finds an article based on ISNI or name
    if re.search('^[0-9 ]*$', searchstring):
        searchstring = searchstring.replace(" ", "")
        data = karp_query('querycount', {'q': "extended||and|swoid.search|equals|%s" % (searchstring)})
    else:
        parts = searchstring.split(" ")
        fornamn = " ".join(parts[0:-1])
        prefix = ""
        last_fornamn = fornamn.split(" ")[-1]
        if last_fornamn == "von" or last_fornamn == "af":
            fornamn = " ".join(fornamn.split(" ")[0:-1])
            prefix = last_fornamn + " "
        efternamn = prefix + parts[-1]
        data = karp_query('querycount', {'q': "extended||and|fornamn.search|contains|%s||and|efternamn.search|contains|%s" % (fornamn, efternamn)})
    # The expected case: only one hit is found
    if data['query']['hits']['total'] == 1:
        url = data['query']['hits']['hits'][0]['_source'].get('url')
        es_id = data['query']['hits']['hits'][0]['_id']
        return data, (url or es_id)
        # Otherwise just return the data
    else:
        return data, ''


def show_article(data, lang="sv"):
    if data['query']['hits']['total'] == 1:
        source = data['query']['hits']['hits'][0]['_source']
        source['url'] = source.get('url') or data['query']['hits']['hits'][0]['_id']
        source['es_id'] = data['query']['hits']['hits'][0]['_id']

        # Print html for the names with the calling name and last name in bold
        formatted_names = helpers.format_names(source, "b")
        source['showname'] = "%s <b>%s</b>" % (formatted_names, source['name'].get('lastname', ''))
        title = "%s %s" % (helpers.format_names(source, ""), source['name'].get('lastname', ''))
        if source.get('text'):
            source['text'] = helpers.markdown_html(helpers.unescape(helpers.mk_links(source['text'])))
        if source.get('text_eng'):
            source['text_eng'] = helpers.markdown_html(helpers.unescape(helpers.mk_links(source['text_eng'])))

        # Extract linked names from source
        source['linked_names'] = find_linked_names(source.get("othernames", {}), source.get("showname"))
        source['othernames'] = helpers.group_by_type(source.get('othernames', {}), 'name')

        helpers.collapse_kids(source)
        if "source" in source:
            source['source'] = helpers.aggregate_by_type(source['source'], use_markdown=True)
        if "furtherreference" in source:
            source['furtherreference'] = helpers.aggregate_by_type(source['furtherreference'], use_markdown=True)
        if type(source["article_author"]) != list:
            source["article_author"] = [source["article_author"]]

        # Set description for meta data
        if lang == "sv":
            description = helpers.get_shorttext(source.get('text', ''))
        else:
            description = helpers.get_shorttext(source.get('text_eng', source.get('text', '')))

        if source.get("portrait"):
            image = source["portrait"][0]["url"]
        else:
            image = ""

        # Sort keywords alphabetically
        kw = source.get("keyword", [])
        collator = icu.Collator.createInstance(icu.Locale('sv_SE.UTF-8'))
        kw.sort(key=lambda x: collator.getSortKey(x))

        under_development = True if source.get("skbl_status") == "Under utveckling" else False

        return render_template('article.html', article=source, article_id=source['es_id'],
                               article_url=source['url'],
                               title=title, description=description, image=image, under_development=under_development)
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
    page = searchresult(result, name='award',
                        searchfield='prisbeskrivning',
                        imagefolder='award', searchtype='equals')
    return set_cache(page)


@app.route("/en/education_institution", endpoint="institution_index_en")
@app.route("/sv/utbildningsinstitution", endpoint="institution_index_sv")
def institution_index():
    # There are no links to this page, but might be wanted later on
    # Exists only to support institution/<result> below
    set_language_switch_link("institution_index")
    return computeviews.bucketcall(queryfield='prisbeskrivning', name='award',
                                   title='Institution', infotext='')


@app.route("/en/education_institution/<result>", endpoint="institution_en")
@app.route("/sv/utbildningsinstitution/<result>", endpoint="institution_sv")
def institution(result=None):
    page = searchresult(result, name='institution', searchfield='utbildningsinstitution', title=result)
    return set_cache(page)


@app.route("/en/article/<id>.json", endpoint="article_json_en")
@app.route("/sv/artikel/<id>.json", endpoint="article_json_sv")
def article_json(id=None):
    data = karp_query('querycount', {'q': "extended||and|url|equals|%s" % (id)})
    if data['query']['hits']['total'] == 1:
        page = jsonify(data['query']['hits']['hits'][0]['_source'])
        return set_cache(page)
    data = karp_query('querycount', {'q': "extended||and|id.search|equals|%s" % (id)})
    if data['query']['hits']['total'] == 1:
        page = jsonify(data['query']['hits']['hits'][0]['_source'])
        return set_cache(page)


### Cache handling ###
@app.route('/emptycache')
def emptycache():
    # Users with write premissions to skbl may empty the cache
    emptied = False
    try:
        emptied = computeviews.compute_emptycache(['article', 'activity',
                                                   'organisation', 'place',
                                                   'artikelforfattare'])
    except Exception:
        emptied = False
        # return jsonify({"error": "%s" % e})
    return jsonify({"cached_emptied": emptied})


@app.route('/cachestats')
def cachestats():
    # Show stats of the cache
    with mc_pool.reserve() as client:
        return jsonify({"cached_stats": client.get_stats()})


@app.route("/en/fillcache", endpoint="fillcache_en")
@app.route("/sv/fillcache", endpoint="fillcache_sv")
def fillcache():
    # Refill the cache (~ touch all pages)
    # This request will take some seconds, users may want to make an
    # asynchronous call
    # Compute new pages
    computeviews.compute_article(cache=False)
    computeviews.compute_activity(cache=False)
    computeviews.compute_organisation(cache=False)
    computeviews.compute_place(cache=False)
    computeviews.compute_artikelforfattare(cache=False)
    lang = 'sv' if 'sv' in request.url_rule.rule else 'en'
    # Copy the pages to the backup fields
    computeviews.copytobackup(['article', 'activity', 'organisation', 'place'], lang)
    return jsonify({"cache_filled": True, "cached_language": lang})


@app.route('/mcpoolid')
def mcpoolid():
    return jsonify({"id": id(mc_pool)})
