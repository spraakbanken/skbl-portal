# -*- coding=utf-8 -*-
from app import g
from flask import url_for
import icu  # pip install PyICU
import markdown
import re
import datetime
import static_info


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
    return datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")


def markdown_html(text):
    return markdown.markdown(text)


def group_by_type(objlist, name):
    newdict = {}
    for obj in objlist:
        val = obj.get(name, "")
        key = obj.get('type', u'Övrigt')
        if key not in newdict:
            newdict[key] = []
        newdict[key].append(val)
    result = []
    for key, val in newdict.items():
        result.append({'type': key, name: ', '.join(val)})
    return result


def make_alphabetical_bucket(result):
    def processname(bucket, results):
        results.append((bucket[0].replace(u"von ", "")[0].upper(), bucket))
    return make_alphabetic(result, processname)


def rewrite_von(input):
    if "von " in input:
        return input.replace("von ", "") + " von"
    else:
        return input


def make_placenames(places):
    def processname(hit, results):
        name = hit['name'].strip()
        results.append((name[0].upper(), (name, hit)))
    return make_alphabetic(places, processname)


def make_alphabetic(hits, processname):
    """ Loops through hits, applies the function 'processname'
        on each object and then sorts the result in alphabetical
        order.
        The function processname should append zero or more processed form of
        the object to the result list.
        This processed forms should be a pair (first_letter, result)
        where first_letter is the first_letter of each object (to sort on), and the result
        is what the html-template want e.g. a pair of (name, no_hits)
    """
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
        if first_letter not in letter_results:
            letter_results[first_letter] = [result]
        else:
            letter_results[first_letter].append(result)

    # Sort result dictionary alphabetically into list
    collator = icu.Collator.createInstance(icu.Locale('sv_SE.UTF-8'))
    for n, items in letter_results.items():
        items.sort(key=lambda x: collator.getSortKey(x[0].replace("von ", "")))
    letter_results = sorted(letter_results.items(), key=lambda x: collator.getSortKey(x[0]))
    return letter_results



def make_simplenamelist(hits):
    """
    Creates a list with links to the entries url or _id
    Sorts entries with names matching the query higher
    """
    results = []
    used = set()
    for order, hit in enumerate(hits["hits"]):
        hitfields = hit["highlight"]
        score = sum(1 for field in hitfields if field.startswith('name.'))
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
        is_link = hit["_index"].startswith("link")
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
    # TODO markdown should fix this itself
    try:
        text = re.sub('\[\]\((.*?)\)', r'[\1](\1)', text)
        for link in re.findall('\]\((.*?)\)', text):
            if link in static_info.more_women:
                text = re.sub('\(%s\)' % link, '(%s)' % url_for('more-women_' + g.language, linked_from=link), text)
            else:
                text = re.sub('\(%s\)' % link, '(%s)' % url_for('article_index_' + g.language, search=link), text)
    except:
        # If there are parenthesis within the links, problems will occur.
        text = text
    return text


def unescape(text):
    return re.sub('&gt;', r'>', text)


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
                types[t].append(item)
    return types.items()


def collapse_kids(source):
    unkown_kids = 0
    for relation in source.get('relation', []):
        if relation.get('type') == 'Barn' and len(relation.keys()) == 1:
            unkown_kids += 1
            relation['hide'] = True
    if unkown_kids:
        source['collapsedrelation'] = [{"type": "Barn", "count": unkown_kids}]


def make_placelist(hits, placename, lat, lon):
    grouped_results = {}
    for hit in hits["hits"]:
        source = hit["_source"]
        hit['url'] = source.get('url') or hit['_id']
        placelocations = {"Bostadsort": source.get('places', []),
                          "Verksamhetsort": source.get('occupation', []),
                          "Utbildningsort": source.get('education', []),
                          "Kontakter": source.get('contact', []),
                          u"Födelseort": [source.get('lifespan', {}).get("from", {})],
                          u"Dödsort": [source.get('lifespan', {}).get("to", {})]
                          }

        for ptype, places in placelocations.items():
            names = dict([(place.get('place', {}).get('place', '').strip(),
                           place.get('place', {}).get('pin', {})) for place in places])
            # check if the name and the lat,lon is correct
            # (we can't ask karp of this, since it would be a nested query)
            if placename in names:
                # Coordinates! If coordinates are used, uncomment the two lines below
                # if names[placename].get('lat') == float(lat)\
                #    and names[placename].get('lon') == float(lon):
                    if ptype not in grouped_results:
                        grouped_results[ptype] = []
                    grouped_results[ptype].append((join_name(hit["_source"], mk_bold=True), hit))
                # else:
                    # These two lines should be removed, but are kept for debugging
                    # if 'Fel' not in grouped_results: grouped_results['Fel'] = []
                    # grouped_results['Fel'].append((join_name(source), hit))

    # Sort result dictionary alphabetically into list

    collator = icu.Collator.createInstance(icu.Locale('sv_SE.UTF-8'))
    for n, items in grouped_results.items():
        items.sort(key=lambda x: collator.getSortKey(x[0]))
    grouped_results = sorted(grouped_results.items(), key=lambda x: collator.getSortKey(x[0]))

    # These two lines should be removed, but are kept for debugging
    # if not grouped_results:
    #     grouped_results = [('Fel', [(join_name(hit['_source']), hit) for hit in hits['hits']])]
    return grouped_results


def is_email_address_valid(email):
    """
    Validate the email address using a regex.
    It may not include any whitespaces, has exactly one "@" and at least one
    "." after the "@".
    """
    if " " in email:
        return False
    # if not re.match("^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*$", email):
    # More permissive regex: does allow non-ascii chars
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False
    return True


def is_ascii(s):
    """Check if s contains of ASCII-characters only."""
    return all(ord(c) < 128 for c in s)


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
    """
    Get the initial 200 characters of text.
    Remove HTML and line breaks.
    """
    shorttext = re.sub(r'<.*?>|\n|\t', ' ', text)
    shorttext = shorttext.strip()
    shorttext = re.sub(r'  ', ' ', shorttext)
    return shorttext[:200]


def get_org_name(organisation):
    """Get short name for organisation (--> org.)"""
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
