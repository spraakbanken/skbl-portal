# -*- coding=utf-8 -*-
"""Define different helper functions."""

import datetime
import re
import sys
import urllib.parse
from urllib.request import Request, urlopen

from flask import url_for, current_app, render_template, g, request, make_response
from flask_babel import gettext
import icu
import json
import markdown

from . import static_info


def set_language_switch_link(route, fragment=None, lang=''):
    """Fix address and label for language switch button."""
    if not lang:
        lang = g.language
    if lang == 'en':
        g.switch_language = {'url': url_for("views." + route + '_sv'), 'label': 'Svenska'}
    else:
        g.switch_language = {'url': url_for("views." + route + '_en'), 'label': 'English'}
    if fragment is not None:
        g.switch_language['url'] += '/' + fragment


def cache_name(pagename, lang=''):
    """Get page from cache."""
    if not lang:
        lang = 'sv' if 'sv' in request.url_rule.rule else 'en'
    return '%s_%s' % (pagename, lang)


def karp_query(action, query, mode=None):
    """Generate query and send request to Karp."""
    if not mode:
        mode = current_app.config['KARP_MODE']
    query['mode'] = mode
    query['resource'] = current_app.config['KARP_LEXICON']
    if 'size' not in query:
        query['size'] = current_app.config['RESULT_SIZE']
    params = urllib.parse.urlencode(query)
    return karp_request("%s?%s" % (action, params))


def karp_request(action):
    """Send request to Karp backend."""
    q = Request("%s/%s" % (current_app.config['KARP_BACKEND'], action))
    if current_app.config['DEBUG']:
        sys.stderr.write("\nREQUEST: %s/%s\n\n" % (current_app.config['KARP_BACKEND'], action))
    if current_app.config.get('USE_AUTH', False):
        q.add_header('Authorization', "Basic %s" % (current_app.config['KARP_AUTH_HASH']))
    response = urlopen(q).read()
    data = json.loads(response.decode("UTF-8"))
    return data


def karp_fe_url():
    """Get URL for Karp frontend."""
    return current_app.config["KARP_FRONTEND"] + "/#?mode=" + current_app.config["KARP_MODE"]


def serve_static_page(page, title=''):
    """Serve static html."""
    set_language_switch_link(page)
    with current_app.open_resource("static/pages/%s/%s.html" % (page, g.language)) as f:
        data = f.read().decode("UTF-8")

    return render_template('page_static.html',
                           content=data,
                           title=title)


def check_cache(page, lang=''):
    """
    Check if page is in cache.

    If the cache should not be used, return None.
    """
    if current_app.config['TEST']:
        return None
    try:
        with g.mc_pool.reserve() as client:
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
    if no_hits >= current_app.config['CACHE_HIT_LIMIT']:
        try:
            with g.mc_pool.reserve() as client:
                client.set(pagename, page, time=current_app.config['LOW_CACHE_TIME'])
        except Exception:
            # TODO what to do??
            pass
    r = make_response(page)
    r.headers.set('Cache-Control', "public, max-age=%s" %
                  current_app.config['BROWSER_CACHE_TIME'])
    return r


def get_first_name(source):
    """Return the given name (first name)."""
    return re.sub('/', '', source['name'].get('firstname', '')).strip()


def format_names(source, fmt="strong"):
    """Return the given name (first name), and the formatted callingname (tilltalsnamnet)."""
    if fmt:
        return re.sub('(.*)/(.+)/(.*)', r'\1<%s>\2</%s>\3' % (fmt, fmt), source['name'].get('firstname', ''))
    else:
        return re.sub('(.*)/(.+)/(.*)', r'\1\2\3', source['name'].get('firstname', ''))


def get_life_range(source):
    """
    Return the birth and death year from _source (as a tuple).

    Return empty strings if not available.
    """
    years = []
    for event in ['from', 'to']:
        if source['lifespan'].get(event):
            date = source['lifespan'][event].get('date', '')
            if date:
                date = date.get('comment', '')
            if "-" in date and not re.search('[a-zA-Z]', date):
                year = date[:date.find("-")]
            else:
                year = date
        else:
            year = ''
        years.append(year)

    return years[0], years[1]


def get_life_range_force(source):
    """
    Return the birth and death year from _source (as a tuple).

    Try to also parse non-dates like "ca. 1500-talet".
    Return -1, 1000000 if not available.
    """

    default_born = -1
    default_died = 1000000

    def convert(event, retval):
        if source['lifespan'].get(event):
            date = source['lifespan'][event].get('date', '')
            if date:
                date = date.get('comment', '')
                match = re.search(r".*(\d{4}).*", date)
                if match:
                    retval = int(match.group(1))
        return retval

    born = convert('from', default_born)
    dead = convert('to', default_died)

    # Sorting hack: if there is no birth year, set it to dead -100 (and vice versa)
    # to make is appear in a more reasonable position in the chronology
    if born == default_born and dead != default_died:
        born = dead - 100
    if dead == default_died and born != default_born:
        dead = born + 100

    return born, dead


def get_date(source):
    """Get birth and death date if available. Return empty strings otherwise."""
    dates = []
    for event in ['from', 'to']:
        if source['lifespan'][event].get('date'):
            date = source['lifespan'][event]['date'].get('comment', '')
        else:
            date = ''
        dates.append(date)

    return dates[0], dates[1]


def get_current_date():
    """Get the current date."""
    return datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")


def markdown_html(text):
    """Convert markdown text to html."""
    return markdown.markdown(text)


def group_by_type(objlist, name):
    """Group objects by their type (=name), e.g. 'othernames'."""
    newdict = {}
    for obj in objlist:
        val = obj.get(name, "")
        key_sv = obj.get('type', u'Övrigt')
        key_en = obj.get('type_eng', u'Other')
        if key_sv not in newdict:
            newdict[key_sv] = (key_en, [])
        newdict[key_sv][1].append(val)
    result = []
    for key, val in list(newdict.items()):
        result.append({'type': key, 'type_eng': val[0], name: ', '.join(val[1])})
    return result


def make_alphabetical_bucket(result, sortnames=False, lang="sv"):
    def processname(bucket, results):
        results.append((bucket[0].replace(u"von ", "")[0].upper(), bucket))
    return make_alphabetic(result, processname, sortnames=sortnames, lang=lang)


def rewrite_von(name):
    """Move 'von' and 'av' to end of name."""
    name = re.sub(r"^von (.+)$", r"\1 von", name)
    name = re.sub(r"^af (.+)$", r"\1 af", name)
    return name


def make_placenames(places, lang="sv"):
    def processname(hit, results):
        name = hit['name'].strip()
        results.append((name[0].upper(), (name, hit)))
    return make_alphabetic(places, processname, lang=lang)


def make_alphabetic(hits, processname, sortnames=False, lang="sv"):
    """
    Loop through hits, apply the function 'processname' on each object and then sort the result in alphabetical order.

    The function processname should append zero or more processed form of
    the object to the result list.
    This processed forms should be a pair (first_letter, result)
    where first_letter is the first_letter of each object (to sort on), and the result
    is what the html-template want e.g. a pair of (name, no_hits)
    """
    def fix_lastname(name):
        name = re.sub(r"(^von )|(^af )", r"", name)
        return name.replace(" ", "z")

    results = []
    for hit in hits:
        processname(hit, results)

    letter_results = {}
    # Split the result into start letters
    for first_letter, result in results:
        if first_letter == u'Ø':
            first_letter = u'Ö'
        if first_letter == u'Æ':
            first_letter = u'Ä'
        if first_letter == u'Ü':
            first_letter = u'Y'
        if lang == "en" and first_letter == u"Ö":
            first_letter = u"O"
        if lang == "en" and first_letter in u"ÄÅ":
            first_letter = u"A"
        if first_letter not in letter_results:
            letter_results[first_letter] = [result]
        else:
            letter_results[first_letter].append(result)

    # Sort result dictionary alphabetically into list
    if lang == "en":
        collator = icu.Collator.createInstance(icu.Locale('en_EN.UTF-8'))
    else:
        collator = icu.Collator.createInstance(icu.Locale('sv_SE.UTF-8'))
    for n, items in list(letter_results.items()):
        if sortnames:
            items.sort(key=lambda x: collator.getSortKey(fix_lastname(x[0]) + " " + x[1]))
        else:
            items.sort(key=lambda x: collator.getSortKey(x[0]))

    letter_results = sorted(list(letter_results.items()), key=lambda x: collator.getSortKey(x[0]))
    return letter_results


def make_simplenamelist(hits):
    """
    Create a list with links to the entries url or _id.

    Sort entries with names matching the query higher.
    """
    results = []
    used = set()
    for order, hit in enumerate(hits["hits"]):
        # ToDo: Ranking of search results partly broken!
        # hitfields = hit["highlight"]
        # score = sum(1 for field in hitfields if field.startswith('name.'))
        score = None
        if score:
            name = join_name(hit["_source"], mk_bold=True)
            liferange = get_life_range(hit["_source"])
            subtitle = hit["_source"].get("subtitle", "")
            subtitle_eng = hit["_source"].get("subtitle_eng", "")
            subject_id = hit["_source"].get('url') or hit["_id"]
            results.append((-score, name, liferange, subtitle, subtitle_eng, subject_id))
            used.add(hit["_id"])
    return sorted(results), used


def make_namelist(hits, exclude=set()):
    """
    Split hits into one list per first letter.

    Return only info necessary for listing of names.
    """
    results = []
    first_letters = []  # list only containing letters in alphabetical order
    current_letterlist = []  # list containing entries starting with the same letter
    for hit in hits["hits"]:
        if hit['_id'] in exclude:
            continue
        # Seperate names from linked names
        is_link = hit["_index"].startswith(current_app.config['SKBL_LINKS'])
        if is_link:
            name = hit["_source"]["name"].get("sortname", "")
            linked_name = join_name(hit["_source"])
        else:
            name = join_name(hit["_source"], mk_bold=True)
            linked_name = False

        liferange = get_life_range(hit["_source"])
        subtitle = hit["_source"].get("subtitle", "")
        subtitle_eng = hit["_source"].get("subtitle_eng", "")
        subject_id = hit["_source"].get('url') or hit["_id"]

        # Get first letter from sort[0]
        firstletter = hit["sort"][1].upper()
        if firstletter not in first_letters:
            if current_letterlist:
                results.append(current_letterlist)
                current_letterlist = []
            first_letters.append(firstletter)
        current_letterlist.append((firstletter, is_link, name, linked_name, liferange, subtitle, subtitle_eng, subject_id))

    if current_letterlist:
        # Append last letterlist
        results.append(current_letterlist)

    return (first_letters, results)


def make_datelist(hits):
    """Extract information relevant for chronology list (same as make_namelist but without letter splitting)."""
    result = []
    for hit in hits:
        is_link = hit["_index"].startswith(current_app.config['SKBL_LINKS'])
        if is_link:
            name = hit["_source"]["name"].get("sortname", "")
            linked_name = join_name(hit["_source"])
        else:
            name = join_name(hit["_source"], mk_bold=True)
            linked_name = False

        liferange = get_life_range(hit["_source"])
        subtitle = hit["_source"].get("subtitle", "")
        subtitle_eng = hit["_source"].get("subtitle_eng", "")
        subject_id = hit["_source"].get('url') or hit["_id"]

        result.append((is_link, name, linked_name, liferange, subtitle, subtitle_eng, subject_id))
    return result


def join_name(source, mk_bold=False):
    """Retrieve and format name from source."""
    name = []
    lastname = source["name"].get("lastname", '')
    match = re.search('(von |af |)(.*)', lastname)
    vonaf = match.group(1)
    lastname = match.group(2)
    if lastname:
        if mk_bold:
            name.append("<strong>%s</strong>," % lastname)
        else:
            name.append(lastname + ",")
    if mk_bold:
        name.append(format_names(source, fmt="strong"))
    else:
        name.append(source['name'].get('firstname', ''))
    name.append(vonaf)
    return " ".join(name)


def sort_places(stat_table, route):
    """Translate place names and sort list."""
    # Work in progress! Waiting for translation list.
    # Or should this be part of the data instead??
    place_translations = {
        u"Göteborg": "Gothenburg"
    }

    if "place" in route.rule:
        lang = "en"
    else:
        lang = "sv"

    if lang == "en":
        for d in stat_table:
            d["display_name"] = place_translations.get(d["name"], d["name"])
    else:
        for d in stat_table:
            d["display_name"] = d["name"]

    stat_table.sort(key=lambda x: x.get('name').strip())
    return stat_table


def mk_links(text):
    """Fix display of links within an article text."""
    # TODO markdown should fix this itself
    try:
        text = re.sub(r'\[\]\((.*?)\)', r'[\1](\1)', text)
        for link in re.findall(r'\]\((.*?)\)', text):
            text = re.sub(r'\(%s\)' % link, '(%s)' % url_for('views.article_index_' + g.language, search=link), text)
    except Exception:
        # If there are parenthesis within the links, problems will occur.
        text = text
    return text


def unescape(text):
    """Unescape some html chars."""
    text = re.sub('&gt;', r'>', text)
    text = re.sub('&apos;', r"'", text)
    return text


def aggregate_by_type(items, use_markdown=False):
    if not isinstance(items, list):
        items = [items]
    types = {}
    for item in items:
        if "type" in item:
            t = item["type"]
            if t:
                if t not in types:
                    types[t] = []
                if use_markdown and "description" in item:
                    item["description"] = markdown_html(item["description"])
                    item["description_eng"] = markdown_html(item.get("description_eng", ""))
                types[t].append(item)
    return list(types.items())


def collapse_kids(source):
    unkown_kids = 0
    for relation in source.get('relation', []):
        if relation.get('type') == 'Barn' and len(list(relation.keys())) == 1:
            unkown_kids += 1
            relation['hide'] = True
    if unkown_kids:
        source['collapsedrelation'] = [{"type": "Barn", "count": unkown_kids}]


def make_placelist(hits, placename, lat, lon):
    grouped_results = {}
    for hit in hits["hits"]:
        source = hit["_source"]
        hit['url'] = source.get('url') or hit['_id']
        placelocations = {gettext("Residence"): source.get('places', []),
                          gettext("Place of activity"): source.get('occupation', []),
                          gettext("Place of education"): source.get('education', []),
                          gettext("Contacts"): source.get('contact', []),
                          gettext("Birthplace"): [source.get('lifespan', {}).get("from", {})],
                          gettext("Place of death"): [source.get('lifespan', {}).get("to", {})]
                          }

        for ptype, places in list(placelocations.items()):
            names = dict([(place.get('place', {}).get('place', '').strip(),
                           place.get('place', {}).get('pin', {})) for place in places])
            # Check if the name and the lat, lon is correct
            # (We can't ask karp of this, since it would be a nested query)
            if placename in names:
                # Coordinates! If coordinates are used, uncomment the two lines below
                # if names[placename].get('lat') == float(lat)\
                #    and names[placename].get('lon') == float(lon):
                if ptype not in grouped_results:
                    grouped_results[ptype] = []
                grouped_results[ptype].append((join_name(hit["_source"], mk_bold=True), hit))
                # else:
                #     # These two lines should be removed, but are kept for debugging
                #     if 'Fel' not in grouped_results: grouped_results['Fel'] = []
                #     grouped_results['Fel'].append((join_name(source), hit))

    # Sort result dictionary alphabetically into list
    collator = icu.Collator.createInstance(icu.Locale('sv_SE.UTF-8'))
    for n, items in list(grouped_results.items()):
        items.sort(key=lambda x: collator.getSortKey(x[0]))
    grouped_results = sorted(list(grouped_results.items()), key=lambda x: collator.getSortKey(x[0]))

    # These two lines should be removed, but are kept for debugging
    # if not grouped_results:
    #     grouped_results = [('Fel', [(join_name(hit['_source']), hit) for hit in hits['hits']])]
    return grouped_results


def is_email_address_valid(email):
    """
    Validate the email address using a regex.

    It may not include any whitespaces, has exactly one "@" and at least one "." after the "@".
    """
    if " " in email:
        return False
    # if not re.match("^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$", email):
    # More permissive regex: does allow non-ascii chars
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False
    return True


def get_lang_text(json_swe, json_eng, ui_lang):
    """Get text in correct language if available."""
    if ui_lang == "en":
        if json_eng:
            return json_eng
        else:
            return json_swe
    else:
        return json_swe


def get_shorttext(text):
    """Get the initial 200 characters of text. Remove HTML and line breaks."""
    shorttext = re.sub(r'<.*?>|\n|\t', ' ', text)
    shorttext = shorttext.strip()
    shorttext = re.sub(r'  ', ' ', shorttext)
    return shorttext[:200]


def get_org_name(organisation):
    """Get short name for organisation (--> org.)."""
    if organisation.endswith("organisation") or organisation.endswith("organization"):
        return organisation[:-9] + "."
    else:
        return organisation


def lowersorted(xs):
    return sorted(xs, key=lambda x: x[0].lower())


def get_infotext(text, rule):
    """
    Get infotext in correct language with Swedish as fallback.

    text = key in the infotext dict
    rule = request.url_rule.rule
    """
    textobj = static_info.infotexter.get(text)
    if "sv" in rule:
        return textobj.get("sv")
    else:
        return textobj.get("en", textobj.get("sv"))
