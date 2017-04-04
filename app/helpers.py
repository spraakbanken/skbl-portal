# -*- coding=utf-8 -*-
import re


def get_first_name(source):
    " Returns the given name (first name), and the callingname (tilltalsnamnet)"
    calling = re.sub('.*/(.*)/.*', r'\1', source['name'].get('firstname', ''))
    firstname = re.sub('/', '', source['name'].get('firstname', '')).strip()
    return firstname, calling


def markdown_html(text):
    return re.sub('\*(.*?)\*', r'<i>\1</i>', text)



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
