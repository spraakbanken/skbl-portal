# -*- coding=utf-8 -*-
import re
import markdown


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
    #return re.sub('\*(.*?)\*', r'<i>\1</i>', text)



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
