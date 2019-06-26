# -*- coding=utf-8 -*-
"""Define helper functions used to compute the different views."""

from collections import defaultdict
import md5
import os.path
import urllib
from urllib2 import urlopen

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from flask import render_template, request
from flask_babel import gettext
import json
import smtplib

from app import app, karp_query, set_language_switch_link, mc_pool, cache_name, check_cache
import helpers
import static_info


def getcache(page, lang, usecache):
    """
    Get cached page.

    Check if the requested page, in language 'lang', is in the cache
    If not, use the backup cache.
    If the cache should not be used, return None
    """
    # Compute the language
    if not lang:
        lang = 'sv' if 'sv' in request.url_rule.rule else 'en'
    if not usecache or app.config['TEST']:
        return None, lang
    pagename = cache_name(page, lang=lang)
    try:
        with mc_pool.reserve() as client:
            # Look for the page, return if found
            art = client.get(pagename)
            if art is not None:
                return art, lang
            # Ff not, look for the backup of the page and return
            art = client.get(pagename + '_backup')
            if art is not None:
                return art, lang
    except Exception:
        # TODO what to do??
        pass
    # If nothing is found, return None
    return None, lang


def copytobackup(fields, lang):
    """Make backups of  all requested fields to their corresponding backup field."""
    for field in fields:
        with mc_pool.reserve() as client:
            art = client.get(field + lang)
            client.set(cache_name(field, lang) + '_backup', art, time=app.config['CACHE_TIME'])


def searchresult(result, name='', searchfield='', imagefolder='', query='',
                 searchtype='equals', title='', authorinfo=False, lang='',
                 show_lang_switch=True, cache=True):
    """Compute the search result."""
    set_language_switch_link("%s_index" % name, result)
    try:
        result = result.encode("UTF-8")
        pagename = name + '_' + urllib.quote(result)
        art = check_cache(pagename, lang)
        if art is not None:
            return art
        show = ','.join(['name', 'url', 'undertitel', 'lifespan', 'undertitel_eng'])
        if query:
            hits = karp_query('minientry', {'q': query, 'show': show})
        else:
            hits = karp_query('minientry',
                              {'q': "extended||and|%s.search|%s|%s" % (searchfield, searchtype, result),
                               'show': show})
        title = title or result.decode("UTF-8")

        no_hits = hits['hits']['total']
        if no_hits > 0:
            picture = None
            if os.path.exists(app.config.root_path + '/static/images/%s/%s.jpg' % (imagefolder, result)):
                picture = '/static/images/%s/%s.jpg' % (imagefolder, result)
            page = render_template('list.html', picture=picture,
                                   alphabetic=True, title=title,
                                   headline=title, hits=hits["hits"],
                                   authorinfo=authorinfo,
                                   show_lang_switch=show_lang_switch)
            if no_hits >= app.config['CACHE_HIT_LIMIT']:
                try:
                    with mc_pool.reserve() as client:
                        client.set(cache_name(pagename, lang), page, time=app.config['CACHE_TIME'])
                except Exception:
                    # TODO what to do?
                    pass
            return page

        else:
            return render_template('page.html', content=gettext('Contents could not be found!'))

    except Exception as e:
        return render_template('page.html',
                               content="%s\n%s: extended||and|%s.search|%s|%s" % (e, app.config['KARP_BACKEND'], searchfield, searchtype, result))


def compute_organisation(lang="", infotext="", cache=True, url=''):
    """Compute organisation view."""
    set_language_switch_link("organisation_index", lang=lang)
    art, lang = getcache('organisation', lang, cache)
    if art is not None:
        return art

    infotext = helpers.get_infotext("organisation", request.url_rule.rule)
    if lang == "en":
        data = karp_query('minientry', {'q': 'extended||and|anything|regexp|.*',
                                        'show': 'organisationsnamn,organisationstyp_eng'})
        typefield = "type_eng"
    else:
        data = karp_query('minientry', {'q': 'extended||and|anything|regexp|.*',
                                        'show': 'organisationsnamn,organisationstyp'})
        typefield = "type"
    nested_obj = {}
    for hit in data['hits']['hits']:
        for org in hit['_source'].get('organisation', []):
            orgtype = helpers.unescape(org.get(typefield, '-'))
            if orgtype not in nested_obj:
                nested_obj[orgtype] = defaultdict(set)
            nested_obj[orgtype][org.get('name', '-')].add(hit['_id'])
    art = render_template('nestedbucketresults.html',
                          results=nested_obj, title=gettext("Organisations"),
                          infotext=infotext, name='organisation', page_url=url)
    try:
        with mc_pool.reserve() as client:
            client.set(cache_name('organisation', lang), art, time=app.config['CACHE_TIME'])
    except Exception:
        # TODO what to do?
        pass
    return art


def compute_activity(lang='', cache=True, url=''):
    """Compute activity view."""
    set_language_switch_link("activity_index", lang=lang)
    art, lang = getcache('activity', lang, cache)

    if art is not None:
        return art

    infotext = helpers.get_infotext("activity", request.url_rule.rule)

    # Fix list with references to be inserted in results
    reference_list = static_info.activities_reference_list
    [ref.append("reference") for ref in reference_list]

    art = bucketcall(queryfield='verksamhetstext', name='activity',
                     title=gettext("Activities"), infotext=infotext,
                     alphabetical=True,
                     description=helpers.get_shorttext(infotext),
                     insert_entries=reference_list,
                     page_url=url)
    try:
        with mc_pool.reserve() as client:
            client.set(cache_name('activity', lang), art, time=app.config['CACHE_TIME'])
    except Exception:
        # TODO what to do?
        pass
    return art


def compute_article(lang='', cache=True, url=''):
    """Compute article view."""
    set_language_switch_link("article_index", lang=lang)
    art, lang = getcache('article', lang, cache)
    if art is not None:
        return art

    show = ','.join(['name', 'url', 'undertitel', 'lifespan', 'undertitel_eng'])
    infotext = helpers.get_infotext("article", request.url_rule.rule)
    if lang == 'sv':
        data = karp_query('minientry', {'q': "extended||and|namn|exists", 'show': show,
                                        'sort': 'sorteringsnamn.sort,sorteringsnamn.init,tilltalsnamn.sort'},
                          mode=app.config['SKBL_LINKS'])
    else:
        data = karp_query('minientry', {'q': "extended||and|namn|exists", 'show': show,
                                        'sort': 'sorteringsnamn.eng_sort,sorteringsnamn.eng_init,sorteringsnamn.sort,tilltalsnamn.sort'},
                          mode=app.config['SKBL_LINKS'])

    art = render_template('list.html',
                          hits=data["hits"],
                          headline=gettext(u'Women A-Z'),
                          alphabetic=True,
                          split_letters=True,
                          infotext=infotext,
                          title='Articles',
                          page_url=url)
    try:
        with mc_pool.reserve() as client:
            client.set(cache_name('article', lang), art, time=app.config['CACHE_TIME'])
    except Exception:
        # TODO what to do?
        pass
    return art


def compute_place(lang="", cache=True, url=''):
    """Compute place view."""
    set_language_switch_link("place_index", lang=lang)
    art, lang = getcache('place', lang, cache)
    if art is not None:
        return art
    infotext = helpers.get_infotext("place", request.url_rule.rule)

    def parse(kw):
        place = kw.get('key')
        # May be used to parse names with or without coordinates:
        # "Lysekil" or "Lysekil|58.275573|11.435558"
        if '|' in place:
            name, lat, lon = place.split('|')
        else:
            name = place.strip()
            lat, lon = 0, 0
        placename = name if name else '%s, %s' % (lat, lon)
        return {'name': placename, 'lat': lat, 'lon': lon,
                'count': kw.get('doc_count')}

    def has_name(kw):
        name = kw.get('key').split('|')[0]
        if name and u"(osäker uppgift)" not in name:
            return name
        else:
            return None

    # To use the coordinates, use 'getplaces' instead of 'getplacenames'
    data = karp_query('getplacenames/' + app.config['KARP_MODE'], {})
    stat_table = [parse(kw) for kw in data['places'] if has_name(kw)]
    art = render_template('places.html',
                          places=stat_table,
                          title=gettext('Placenames'),
                          infotext=infotext,
                          description=helpers.get_shorttext(infotext),
                          page_url=url)
    try:
        with mc_pool.reserve() as client:
            client.set(cache_name('place', lang), art, time=app.config['CACHE_TIME'])
    except Exception:
        # TODO what to do?
        pass
    return art


def compute_artikelforfattare(infotext='', description='', lang="", cache=True, url=''):
    """Compute authors view."""
    set_language_switch_link("articleauthor_index", lang=lang)
    art, lang = getcache('author', lang, cache)
    if art is not None:
        return art
    q_data = {'buckets': 'artikel_forfattare_fornamn.bucket,artikel_forfattare_efternamn.bucket'}
    data = karp_query('statlist', q_data)
    # strip kw0 to get correct sorting
    stat_table = [[kw[0].strip()] + kw[1:] for kw in data['stat_table'] if kw[0] != ""]
    stat_table = [[kw[1] + ',', kw[0], kw[2]] for kw in stat_table]

    # Remove duplicates and some wrong ones (because of backend limitation):
    stoplist = {
        u"Grevesmühl,Kajsa": True,
        u"Ohrlander,Anders": True,
        u"Myrberg Burström,Mats": True,
        u"Burström,Nanouschka": True,
        u"Ljung,Yvonne": True,
        u"Lindholm,Barbro": True
    }
    added = {}
    new_stat_table = []
    for item in stat_table:
        fullname = item[0] + item[1]
        if fullname not in added and fullname not in stoplist:
            new_stat_table.append(item)
            added[fullname] = True
    art = render_template('bucketresults.html', results=new_stat_table,
                          alphabetical=True, title=gettext('Article authors'),
                          name='articleauthor', infotext=infotext,
                          description=description, sortnames=True,
                          page_url=url)
    try:
        with mc_pool.reserve() as client:
            client.set(cache_name('author', lang), art, time=app.config['CACHE_TIME'])
    except Exception:
        # TODO what to do?
        pass
    return art


def bucketcall(queryfield='', name='', title='', sortby='', lastnamefirst=False,
               infotext='', description='', query='', alphabetical=False,
               insert_entries=None, page_url=''):
    """Bucket call helper."""
    q_data = {'buckets': '%s.bucket' % queryfield}
    if query:
        q_data['q'] = query
    data = karp_query('statlist', q_data)
    # Strip kw0 to get correct sorting
    stat_table = [[kw[0].strip()] + kw[1:] for kw in data['stat_table'] if kw[0] != ""]

    # Insert entries that function as references
    if insert_entries:
        stat_table.extend(insert_entries)
    if sortby:
        stat_table.sort(key=sortby)
    else:
        stat_table.sort()
    if lastnamefirst:
        stat_table = [[kw[1] + ',', kw[0], kw[2]] for kw in stat_table]
    # if showfield:
    #     stat_table = [[showfield(kw), kw[2]] for kw in stat_table]
    return render_template('bucketresults.html', results=stat_table,
                           alphabetical=alphabetical, title=gettext(title),
                           name=name, infotext=infotext,
                           description=description,
                           page_url=page_url)


def compute_emptycache(fields):
    """
    Empty the cache (but leave the backupfields).

    Only users with write permission may do this
    May raise error, eg if the authorization does not work
    """
    emptied = False
    auth = request.authorization
    postdata = {}
    user, pw = auth.username, auth.password
    postdata["username"] = user
    postdata["password"] = pw
    postdata["checksum"] = md5.new(user + pw + app.config['SECRET_KEY']).hexdigest()
    server = app.config['WSAUTH_URL']
    contents = urlopen(server, urllib.urlencode(postdata)).read()
    auth_response = json.loads(contents)
    lexitems = auth_response.get("permitted_resources", {})
    rights = lexitems.get("lexica", {}).get(app.config['KARP_LEXICON'], {})
    if rights.get('write'):
        with mc_pool.reserve() as client:
            for field in fields:
                client.delete(field + 'sv')
                client.delete(field + 'en')
        emptied = True
    return emptied


def compute_contact_form():
    """Compute view for contact form ."""
    set_language_switch_link("contact")

    email = request.form['email'].strip()
    required_fields = ["name", "email"]

    if request.form['mode_switch'] == 'suggest_new':
        mode = "suggestion"
        required_fields.extend(["subject_name", "subject_lifetime",
                               "subject_activity", "motivation"])
    elif request.form['mode_switch'] == 'correction':
        mode = "correction"
        required_fields.append("message")
    else:
        mode = "other"
        required_fields.append("message")

    error_msgs = []
    errors = []
    for field in required_fields:
        if not request.form[field]:
            error_msgs.append(gettext("Please enter all the fields!"))
            errors.append(field)

    if email and not helpers.is_email_address_valid(email):
        error_msgs.append(gettext("Please enter a valid email address!"))

    # Render error messages and tell user what went wrong
    error_msgs = list(set(error_msgs))
    if error_msgs:
        return render_template("contact.html",
                               title=gettext("Contact"),
                               headline=gettext("Contact SKBL"),
                               errors=error_msgs,
                               name_error=True if "name" in errors else False,
                               email_error=True if "email" in errors else False,
                               message_error=True if "message" in errors else False,
                               subject_name_error=True if "subject_name" in errors else False,
                               subject_lifetime_error=True if "subject_lifetime" in errors else False,
                               subject_activity_error=True if "subject_activity" in errors else False,
                               motivation_error=True if "motivation" in errors else False,
                               form_data=request.form,
                               mode=mode)

    else:
        return make_email(request.form, mode)


def make_email(form_data, mode="other"):
    """Compose and send email from contact form."""
    email = form_data["email"]
    msg = MIMEMultipart("alternative")

    if mode == "suggestion":
        text = [u"%s har skickat in ett förslag för en ny SKBL-ingång.\n\n" % form_data["name"]]
        text.append(u"Förslag på kvinna: %s\n" % form_data["subject_name"])
        text.append(u"Kvinnas levnadstid: %s\n" % form_data["subject_lifetime"])
        text.append(u"Kvinnas verksamhet: %s\n" % form_data["subject_activity"])
        text.append(u"Motivering: %s\n" % form_data["motivation"])
        text = u"".join(text)
        subject = u"Förslag för ny ingång i skbl.se"
    elif mode == "correction":
        text = u"%s har skickat följande meddelande:\n\n%s" % (form_data["name"], form_data["message"])
        subject = u"Förslag till rättelse (skbl.se)"
    else:
        text = u"%s har skickat följande meddelande:\n\n%s" % (form_data["name"], form_data["message"])
        subject = u"Förfrågan från skbl.se"

    html = text.replace("\n", "<br>")
    part1 = MIMEText(text, "plain", "utf-8")
    part2 = MIMEText(html, "html", "utf-8")

    msg.attach(part1)
    msg.attach(part2)

    msg["Subject"] = subject
    msg['To'] = app.config['EMAIL_RECIPIENT']

    # Work-around: things won't be as pretty if email adress contains non-ascii chars
    if helpers.is_ascii(form_data["email"]):
        msg['From'] = "%s <%s>" % (Header(form_data["name"], 'utf-8'), form_data["email"])
    else:
        msg['From'] = u"%s <%s>" % (form_data["name"], form_data["email"])
        email = ""

    server = smtplib.SMTP("localhost")
    server.sendmail(email, [app.config['EMAIL_RECIPIENT']], msg.as_string())
    server.quit()

    # Render user feedback
    return render_template("form_submitted.html",
                           title=gettext("Thank you for your feedback") + "!",
                           headline=gettext("Thank you for your feedback") + ", " + form_data["name"].strip() + "!",
                           text=gettext("We will get back to you as soon as we can."))
