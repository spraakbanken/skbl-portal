# -*- coding=utf-8 -*-
import icu # pip install PyICU
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
    birth_date = source['lifespan']['from'].get('date', '')
    if birth_date:
        birth_date = birth_date.get('comment', '')
    if "-" in birth_date:
        birth_year = birth_date[:birth_date.find("-")]
    else:
        birth_year = birth_date

    death_date = source['lifespan']['to'].get('date', '')
    if death_date:
        death_date = death_date.get('comment', '')
    if "-" in death_date:
        death_year = death_date[:death_date.find("-")]
    else:
        death_year = death_date
    if not (birth_year or death_year):
        return False
    return birth_year, death_year


def get_date(source):
    if not source['lifespan']['from'].get('date'):
        return get_life_range(source)
    elif not source['lifespan']['from']['date'].get('date'):
        return False
    if not source['lifespan']['to'].get('date'):
        return get_life_range(source)
    elif not source['lifespan']['to']['date'].get('date'):
        return False
    else:
        return source['lifespan']['from']['date']['date'], source['lifespan']['to']['date']['date']


def markdown_html(text):
    return markdown.markdown(text)


def group_by_type(objlist, name):
    newdict = {}
    for obj in objlist:
        val = obj[name]
        key = obj.get('type', u'Övrigt')
        if key not in newdict:
            newdict[key] = []
        newdict[key].append(val)
    result = []
    for key, val in newdict.items():
        result.append({'type': key, name: ', '.join(val)})
    return result


def make_namelist(hits, alphabetic=True):
    results = []
    for hit in hits["hits"]:
        source = hit["_source"]
        name = get_name(source)
        results.append((join_name(source), name[0][0].upper(), False, hit))
        for altname in source.get("othernames", []):
            if altname.get("mk_link"):
                results.append((altname["name"], altname["name"][0].upper(), True, hit))

    letter_results = {}
    # Split the result into start letters
    for listed_name, first_letter, islink, hit in results:
        if first_letter == u'Ø':
            first_letter = u'Ö'
        if first_letter == u'Æ':
            first_letter = u'Ä'
        if first_letter == u'Ü':
            first_letter = u'Y'
        if first_letter not in letter_results:
            letter_results[first_letter] = [(listed_name, islink, hit)]
        else:
            letter_results[first_letter].append((listed_name, islink, hit))

    # Sort result dictionary alphabetically into list
    if alphabetic:
        collator = icu.Collator.createInstance(icu.Locale('sv_SE.UTF-8'))
        letter_results = sorted(letter_results.items(), key=lambda x: collator.getSortKey(x[0]))
    else:
        letter_results = list(letter_results.items())

    return letter_results


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

def aggregate_by_type(items, use_markdown=False):
    if not isinstance(items, list):
        items = [items]
    types = {}
    for item in items:
        if "type" in item:
            t = item["type"]
            if t:
                if not t in types:
                    types[t] = []
                if use_markdown:
                    item["description"] = markdown_html(item["description"])
                types[t].append(item)
    return types.items()
