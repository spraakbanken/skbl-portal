import os
from flask import Flask, request, redirect, render_template, url_for, g
from flask_babel import Babel
from setuptools import setup

app = Flask(__name__)

app.config.from_object('config')
babel = Babel(app)



@babel.localeselector
def get_locale():
    lang = request.path[1:].split('/', 1)[0]
    user = getattr(g, 'user', None)
    if lang in ['sv', 'en']:
        return lang
    elif user is not None:
        return user.locale
    else:
        return request.accept_languages.best_match(['sv', 'en'])

def get_language_swith_link(route):
    if(get_locale() == 'en'):
        g.switch_language = {'url': url_for(route+'_sv'), 'label' : 'Svenska'}
    else:
        g.switch_language = {'url': url_for(route+'_en'), 'label':'English'}

@app.before_request
def func():
    g.babel = Babel
    g.language = get_locale()

@app.context_processor
def inject_custom():
    d = {'lurl_for': lambda ep, **kwargs: url_for(ep+'_'+g.language, **kwargs)}
    return d

from app import views