# -*- coding=utf-8 -*-
from app import app, karp_query, render_template, request, set_language_switch_link
from collections import defaultdict
from flask_babel import gettext
import icu  # pip install PyICU
import json
import md5
import urllib
from urllib2 import urlopen


def compute_organisation(client, lang=""):
    set_language_switch_link("organisation_index", lang=lang)
    if not lang:
        lang = 'sv' if 'sv' in request.url_rule.rule else 'en'
    art = client.get('organisation' + lang)
    if art is not None and not app.config['TEST']:
        return art

    if lang == 'sv':
        infotext = u"""Här kan du se vilka organisationer de biograferade kvinnorna varit medlemmar
        och verksamma i. Det ger en inblick i de nätverk som var de olika kvinnornas och visar
        såväl det gemensamma engagemanget som mångfalden i det.
        Om du klickar på organisationens namn visas vilka kvinnor som var aktiva i den."""
    else:
        infotext = u"""This displays the organisations which the subjects in the dictionary joined
        and within which they were active. This not only provides an insight into each woman’s
        networks but also highlights both shared activities and their diversity.
        Selecting a particular organisation generates a list of all women who were members."""

    data = karp_query('minientry', {'q': 'extended||and|anything|regexp|.*',
                                    'show': 'organisationsnamn,organisationstyp'})
    nested_obj = {}
    for hit in data['hits']['hits']:
        for org in hit['_source'].get('organisation', []):
            orgtype = org.get('type', '-')
            if orgtype not in nested_obj:
                nested_obj[orgtype] = defaultdict(set)
            nested_obj[orgtype][org.get('name', '-')].add(hit['_id'])
    art = render_template('nestedbucketresults.html',
                          results=nested_obj, title=gettext("Organisations"),
                          infotext=infotext, name='organisation')
    client.set('organisation' + lang, art, time=app.config['CACHE_TIME'])
    return art
    # return bucketcall(queryfield='organisationstyp', name='organisation',
    #                   title='Organizations', infotext=infotext)


def compute_activity(client, lang=""):
    set_language_switch_link("activity_index", lang=lang)
    if not lang:
        lang = 'sv' if 'sv' in request.url_rule.rule else 'en'
    art = client.get('activity' + lang)
    if art is not None and not app.config['TEST']:
        return art
    if lang == 'sv':
        infotext = u"Här kan du se inom vilka områden de biograferade kvinnorna varit verksamma och vilka yrken de hade."
    else:
        infotext = u"This displays the areas within which the biographical subject was active and which activities and occupation(s) they engaged in."
    art = bucketcall(queryfield='verksamhetstext', name='activity',
                     title=gettext("Activities"), infotext=infotext,
                     alphabetical=True)
    client.set('activity' + lang, art, time=app.config['CACHE_TIME'])
    return art


def compute_article(client, lang=""):
    set_language_switch_link("article_index", lang=lang)
    if not lang:
        lang = 'sv' if 'sv' in request.url_rule.rule else 'en'
    art = client.get('article' + lang)
    if art is not None and not app.config['TEST']:
        return art
    else:
        if lang == 'sv':
            infotext = u"""Klicka på namnet för att läsa biografin om den kvinna du vill veta mer om."""
            data = karp_query('query', {'q': "extended||and|namn|exists"}, mode="skbllinks")
        else:
            infotext = u"""Klicka på namnet för att läsa biografin om den kvinna du vill veta mer om."""
            data = karp_query('query', {'q': "extended||and|namn|exists", 'sort': 'sorteringsnamn.eng_init,sorteringsnamn.eng_sort,sorteringsnamn,tilltalsnamn.sort,tilltalsnamn'},
                              mode="skbllinks")

        art = render_template('list.html',
                              hits=data["hits"],
                              headline=gettext(u'Women A-Z'),
                              alphabetic=True,
                              split_letters=True,
                              infotext=infotext,
                              title='Articles')
        client.set('article' + lang, art, time=app.config['CACHE_TIME'])
    return art


def compute_place(client, lang=""):
    set_language_switch_link("place_index", lang=lang)
    if not lang:
        lang = 'sv' if 'sv' in request.url_rule.rule else 'en'
    rv = client.get('place' + lang)
    if rv is not None and not app.config['TEST']:
        return rv

    if lang == 'sv':
        infotext = u"""Här kan du se var de biograferade kvinnorna befunnit sig;
        var de fötts, verkat och dött. Genom att klicka på en ord kan du se vilka som fötts,
        verkat och/eller avlidit där."""
    else:
        infotext = u"""This displays the subjects’ locations: where they were born
        where they were active, and where they died. Selecting a particular placename
        generates a list of all subjects who were born, active and/or died at that place."""

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
    data = karp_query('getplacenames', {})
    stat_table = [parse(kw) for kw in data['places'] if has_name(kw)]
    # Sort and translate
    # stat_table = helpers.sort_places(stat_table, request.url_rule)
    collator = icu.Collator.createInstance(icu.Locale('sv_SE.UTF-8'))
    stat_table.sort(key=lambda x: collator.getSortKey(x.get('name').strip()))
    art = render_template('places.html', places=stat_table, title=gettext("Placenames", infotext=infotext))
    client.set('place' + lang, art, time=app.config['CACHE_TIME'])
    return art


def bucketcall(queryfield='', name='', title='', sortby='',
               lastnamefirst=False, infotext='', query='', alphabetical=False):
    q_data = {'buckets': '%s.bucket' % queryfield}
    if query:
        q_data['q'] = query
    data = karp_query('statlist', q_data)
    # strip kw0 to get correct sorting
    stat_table = [[kw[0].strip()] + kw[1:] for kw in data['stat_table'] if kw[0] != ""]
    if sortby:
        stat_table.sort(key=sortby)
    else:
        stat_table.sort()
    if lastnamefirst:
        stat_table = [[kw[1] + ',', kw[0], kw[2]] for kw in stat_table]
    return render_template('bucketresults.html', results=stat_table,
                           alphabetical=alphabetical, title=gettext(title),
                           name=name, infotext=infotext)


def compute_emptycache(client):
    # Empty the cache.
    # Only users with write permission may do this
    # May raise error, eg if the authorization does not work
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
    rights = lexitems.get("lexica", {}).get(app.config['SKBL'], {})
    if rights.get('write'):
        client.flush_all()
        emptied = True
    return emptied