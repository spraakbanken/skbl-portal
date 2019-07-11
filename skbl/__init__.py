# -*- coding: utf-8 -*
"""Initialise Flask application."""
import os

from flask import Flask, g, request, url_for
from flask_babel import Babel
from flask_compress import Compress
import html.parser
from pylibmc import Client, ClientPool


def create_app():
    """Instanciate app."""
    app = Flask(__name__)

    if os.path.exists(app.config.root_path + '/config.cfg') is False:
        print("copy config.default.cfg to config.cfg and add your settings")
        app.config.from_pyfile(app.config.root_path + '/config.default.cfg')
    else:
        app.config.from_pyfile(app.config.root_path + '/config.cfg')

    babel = Babel(app)
    Compress(app)

    @babel.localeselector
    def get_locale():
        """Get correct language from url."""
        locale = request.path[1:].split('/', 1)[0]
        if locale in ['sv', 'en']:
            return locale
        else:
            locale = 'sv'
            for lang in list(request.accept_languages.values()):
                if lang[:2] in ['sv', 'en']:
                    locale = lang[:2]
                    break

            g.locale = locale
            return locale

    client = Client(app.config['MEMCACHED'])

    @app.before_request
    def func():
        g.babel = Babel
        g.language = get_locale()
        g.config = app.config
        g.mc_pool = ClientPool(client, app.config['POOL_SIZE'])

    @app.context_processor
    def inject_custom():
        d = {'lurl_for': lambda ep,
             **kwargs: url_for(ep + '_' + g.language, **kwargs)}
        return d

    @app.template_filter('deescape')
    def deescape_filter(s):
        html_parser = html.parser.HTMLParser()
        return html_parser.unescape(s)

    from . import helpers

    app.jinja_env.globals.update(get_life_range=helpers.get_life_range)
    app.jinja_env.globals.update(make_namelist=helpers.make_namelist)
    app.jinja_env.globals.update(make_simplenamelist=helpers.make_simplenamelist)
    app.jinja_env.globals.update(make_placelist=helpers.make_placelist)
    app.jinja_env.globals.update(make_placenames=helpers.make_placenames)
    app.jinja_env.globals.update(
        make_alphabetical_bucket=helpers.make_alphabetical_bucket)
    app.jinja_env.globals.update(
        make_alpha_more_women=helpers.make_alpha_more_women)
    app.jinja_env.globals.update(get_date=helpers.get_date)
    app.jinja_env.globals.update(join_name=helpers.join_name)
    app.jinja_env.globals.update(sorted=sorted)
    app.jinja_env.globals.update(len=len)
    app.jinja_env.globals.update(get_lang_text=helpers.get_lang_text)
    app.jinja_env.globals.update(get_shorttext=helpers.get_shorttext)
    app.jinja_env.globals.update(get_org_name=helpers.get_org_name)
    app.jinja_env.globals.update(rewrite_von=helpers.rewrite_von)
    app.jinja_env.globals.update(lowersorted=helpers.lowersorted)
    app.jinja_env.globals.update(get_current_date=helpers.get_current_date)
    app.jinja_env.globals.update(karp_fe_url=helpers.karp_fe_url)

    from . import views
    app.register_blueprint(views.bp)
    app.register_error_handler(Exception, views.page_not_found)

    return app


# if __name__ == '__main__':
#     if sys.version_info.major < 3:
#         reload(sys)
#     sys.setdefaultencoding('utf8')
#     app.run()
