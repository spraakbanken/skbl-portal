# -*- mode: python; coding: utf-8 -*-

"""
Script for enabling login.
"""

# 140911 cjs: Implemented poor *man's session handling. It's possible
#             for an authenticated user to keep their session active
#             even after a password change by continuously renewing it
#             within WSAUTH_INTERVAL seconds.

import urllib
import urllib2
import md5
import json
import os
import time
# import ConfigParser

WSAUTH_URL = 'https://ws.spraakbanken.gu.se/wsauth/authenticate'
WSAUTH_SECRET_KEY = 'RYO177q8ylTGrQqqtTmyrkCV0YwK6W5B4FvvVBW4YdeBcLF'
# Seconds to cache auth replies
WSAUTH_INTERVAL = 300
SESSIONDIR = '/tmp/skbl/sessions'

# configParser = ConfigParser.RawConfigParser()


def check_password(environ, user, password):
    # try:
    #     configParser.read("config.cfg")
    #     require_login = configParser.get("config", "REQUIRE_LOGIN")
    #     if require_login is False:
    #         return True
    # except:
    #     # FIXA: Vad gör vi nu?
    #     pass
    if not os.path.isdir(SESSIONDIR):
        os.makedirs(SESSIONDIR)

    user = user.decode("raw_unicode_escape").encode("utf-8")
    password = password.decode("raw_unicode_escape").encode("utf-8")

    sessionfile = os.path.join(SESSIONDIR, md5.new(user + password).hexdigest())

    if os.path.isfile(sessionfile) and (time.time() - os.path.getmtime(sessionfile)) < WSAUTH_INTERVAL:
        os.utime(sessionfile, None)
        return True

    wsauth_data = {
        'username': user,
        'password': password,
        'checksum': md5.new(user + password + WSAUTH_SECRET_KEY).hexdigest()
    }

    try:
        response = json.loads(urllib2.urlopen(WSAUTH_URL, urllib.urlencode(wsauth_data)).read())

        if response['authenticated'] and \
           'lexica' in response['permitted_resources'] and \
           'skbl' in response['permitted_resources']['lexica'] and \
           response['permitted_resources']['lexica']['skbl']['read']:
            # Update mtime on sessionfile, but first create it if it doesn't exist
            open(sessionfile, 'w').close()
            os.utime(sessionfile, None)
            return True
    except:
        # FIXA: Vad gör vi nu?
        pass

    return False
