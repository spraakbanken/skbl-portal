"""Initialise Flask application."""

import html
import logging
import re
from pathlib import Path

import flask_reverse_proxy
from flask import Flask, g, request, url_for
from flask_babel import Babel
from flask_compress import Compress
from pylibmc import Client, ClientPool

logger = logging.getLogger(__name__)


def create_app():
    """Instantiate app."""
    app = Flask(__name__)

    if not Path(f"{app.config.root_path}/config.cfg").exists():
        logger.warning("copy config.default.cfg to config.cfg and add your settings")
        app.config.from_pyfile(f"{app.config.root_path}/config.default.cfg")
    else:
        app.config.from_pyfile(f"{app.config.root_path}/config.cfg")

    babel = Babel(app)
    Compress(app)

    babel.init_app(app, locale_selector=get_locale)

    client = Client(app.config["MEMCACHED"])

    @app.before_request
    def func():
        g.babel = Babel
        g.language = get_locale()
        g.config = app.config
        g.mc_pool = ClientPool(client, app.config["POOL_SIZE"])

    @app.context_processor
    def inject_custom():
        return {"lurl_for": lambda ep, **kwargs: url_for(f"{ep}_{g.language}", **kwargs)}

    @app.template_filter("deescape")
    def deescape_filter(s):
        return html.unescape(s)

    @app.template_filter("cclink")
    def cclink_filter(s):
        return re.sub(
            r"(CC-BY\S*)",
            '<a href="https://creativecommons.org/licenses/" target="_blank">\\1</a>',
            s,
        )

    from . import helpers  # noqa: PLC0415

    app.jinja_env.globals.update(get_life_range=helpers.get_life_range)
    app.jinja_env.globals.update(make_namelist=helpers.make_namelist)
    app.jinja_env.globals.update(make_datelist=helpers.make_datelist)
    app.jinja_env.globals.update(make_simplenamelist=helpers.make_simplenamelist)
    app.jinja_env.globals.update(make_placelist=helpers.make_placelist)
    app.jinja_env.globals.update(make_placenames=helpers.make_placenames)
    app.jinja_env.globals.update(make_alphabetical_bucket=helpers.make_alphabetical_bucket)
    app.jinja_env.globals.update(get_date=helpers.get_date)
    app.jinja_env.globals.update(join_name=helpers.join_name)
    app.jinja_env.globals.update(swedish_translator=helpers.swedish_translator)
    app.jinja_env.globals.update(sorted=sorted)
    app.jinja_env.globals.update(len=len)
    app.jinja_env.globals.update(get_lang_text=helpers.get_lang_text)
    app.jinja_env.globals.update(get_shorttext=helpers.get_shorttext)
    app.jinja_env.globals.update(get_org_name=helpers.get_org_name)
    app.jinja_env.globals.update(rewrite_von=helpers.rewrite_von)
    app.jinja_env.globals.update(lowersorted=helpers.lowersorted)
    app.jinja_env.globals.update(get_current_date=helpers.get_current_date)
    app.jinja_env.globals.update(karp_fe_url=helpers.karp_fe_url)

    from . import views  # noqa: PLC0415

    app.register_blueprint(views.bp)
    app.register_error_handler(Exception, views.page_not_found)

    app.wsgi_app = flask_reverse_proxy.ReverseProxied(app.wsgi_app)
    return app


SUPPORTED_LOCALES = {"sv", "en"}


def get_locale():
    """Get correct language from url."""
    locale = request.path[1:].split("/", 1)[0]
    if locale in SUPPORTED_LOCALES:
        return locale
    locale = "sv"
    for lang in list(request.accept_languages.values()):
        if lang[:2] in SUPPORTED_LOCALES:
            locale = lang[:2]
            break

    g.locale = locale
    return locale


# if __name__ == '__main__':
#     if sys.version_info.major < 3:
#         reload(sys)
#     sys.setdefaultencoding('utf8')
#     app.run()
