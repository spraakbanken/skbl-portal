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
    "Return the birth and death year from _source (as a tuple)"
    birth_date = source['lifespan']['from'].get('date', '')
    if birth_date:
        birth_date = birth_date.get('comment', '')
    if "-" in birth_date:
        birth_year = birth_date[:birth_date.find("-")]
    else:
        birth_year = birth_date

    death_date = source['lifespan']['from'].get('date', '')
    if death_date:
        death_date = death_date.get('comment', '')
    if "-" in birth_date:
        death_year = death_date[:death_date.find("-")]
    else:
        death_year = death_date
    return birth_year, death_year


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


def make_namelist(hits):
    results = []
    for hit in hits["hits"]:
        source = hit["_source"]
        name = []
        lastname = source["name"].get("lastname", '')
        match = re.search('(von |af |)(.*)', lastname)
        vonaf = match.group(1)
        lastname = match.group(2)
        if lastname:
            name.append(lastname+",")
        name.append(get_first_name(source)[0])
        name.append(vonaf)
        results.append((' '.join(name), hit))
        for altname in source.get("othernames", []):
            if altname.get("mk_link"):
                results.append((altname["name"], hit))
    collator = icu.Collator.createInstance(icu.Locale('sv_SE.UTF-8'))
    results.sort(key=lambda x:collator.getSortKey(x[0]))
    return results


def sort_places(stat_table, route):
    """Tranlate place names and sort list."""
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
