# -*- coding=utf-8 -*-
from app import g
from flask import url_for
import icu  # pip install PyICU
import markdown
import re


def get_first_name(source):
    "Return the given name (first name), and the callingname (tilltalsnamnet)"
    calling = re.sub('.*/(.*)/.*', r'\1', source['name'].get('firstname', ''))
    firstname = re.sub('/', '', source['name'].get('firstname', '')).strip()
    return firstname, calling


def get_life_range(source):
    """
    Return the birth and death year from _source (as a tuple).
    If both are empty return False.
    """
    if source['lifespan'].get('from'):
        birth_date = source['lifespan']['from'].get('date', '')
        if birth_date:
            birth_date = birth_date.get('comment', '')
        if "-" in birth_date:
            birth_year = birth_date[:birth_date.find("-")]
        else:
            birth_year = birth_date
    else:
        birth_year = ''

    if source['lifespan'].get('to'):
        death_date = source['lifespan']['to'].get('date', '')
        if death_date:
            death_date = death_date.get('comment', '')
        if "-" in death_date:
            death_year = death_date[:death_date.find("-")]
        else:
            death_year = death_date
    else:
        death_year = ''

    return birth_year, death_year


def get_date(source):
    """Get exact birth date if possible. Get date comment otherwise."""
    if not source['lifespan']['from'].get('date'):
        birth_date = get_life_range(source)[0]
        if not birth_date:
            birth_date = ''
    elif source['lifespan']['from']['date'].get('date'):
        birth_date = source['lifespan']['from']['date']['date']
    elif source['lifespan']['from']['date'].get('comment'):
        birth_date = source['lifespan']['from']['date']['comment']
    else:
        birth_date = ''

    if not source['lifespan']['to'].get('date'):
        death_date = get_life_range(source)[1]
        if not death_date:
            death_date = ''
    elif source['lifespan']['to']['date'].get('date'):
        death_date = source['lifespan']['to']['date']['date']
    elif source['lifespan']['to']['date'].get('comment'):
        death_date = source['lifespan']['to']['date']['comment']
    else:
        death_date = ''

    return birth_date, death_date


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
        results.append((bucket[0][0].upper(), bucket))
    return make_alphabetic(result, processname)


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
        items.sort(key=lambda x: collator.getSortKey(x[0]))
    letter_results = sorted(letter_results.items(), key=lambda x: collator.getSortKey(x[0]))
    return letter_results


def make_namelist(hits, alphabetic=True):
    # TODO NB! If alphabetic is set to False, the order will be radom-ish.
    # It will partly follow ES sorting order, but since the dictionary
    # letter_results won't keep the order of the initial letters, the result
    # will be mixed up. Nor will links be sorted accurately. Improve this!
    def processname(hit, results):
        source = hit["_source"]
        name = get_name(source)
        results.append((name[0][0].upper(), (join_name(source), False, hit)))
        for altname in source.get("othernames", []):
            if altname.get("mk_link"):
                results.append((altname["name"][0].upper(),
                                (altname["name"], True, hit)))
    return make_alphabetic(hits["hits"], processname)


def get_name(source):
    name = []
    lastname = source["name"].get("lastname", '')
    match = re.search('(von |af |)(.*)', lastname)
    vonaf = match.group(1)
    lastname = match.group(2)
    if lastname:
        name.append(lastname + ",")
    name.append(get_first_name(source)[0])
    name.append(vonaf)
    return name


def join_name(source):
    return " ".join(get_name(source))


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
            text = re.sub('\(%s\)' % link, '(%s)' % url_for('article_index_' + g.language, search=link), text)
    except:
        # If there are parenthesis within the links, problems will occur.
        text = text
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
                    grouped_results[ptype].append((join_name(source), hit))
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
