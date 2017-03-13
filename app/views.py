import os
import os.path
from app import app, redirect, render_template, request, get_locale, set_language_swith_link, g, serve_static_page, karp_query, karp_request
from flask_babel import gettext
from urllib2 import Request, urlopen 


#redirect to specific language landing-page
@app.route('/')
def index():
    return redirect('/'+get_locale())


@app.route('/en', endpoint='index_en')
@app.route('/sv', endpoint='index_sv')
def start():
    set_language_swith_link("index")
    return render_template('page.html', content='skbl.se')


@app.route("/en/about-skbl", endpoint="about-skbl_en")
@app.route("/sv/om-skbl", endpoint="about-skbl_sv")
def about_skbl():
    return serve_static_page("about-skbl", gettext("About SKBL"))


@app.route("/en/about-us", endpoint="about-us_en")
@app.route("/sv/om-oss", endpoint="about-us_sv")
def about_us():
    return serve_static_page("about-us", gettext("About us"))


@app.route("/en/contact", endpoint="contact_en")
@app.route("/sv/kontakt", endpoint="contact_sv")
def contact():
    return serve_static_page("contact", gettext("Contact"))


@app.route("/en/search", endpoint="search_en")
@app.route("/sv/sok", endpoint="search_sv")
def search():
    set_language_swith_link("search")
    data = karp_query("extended||and|anything.search|equals|%s" % (request.args.get('q', '*')))
    return render_template('search.html', hits = data["query"]["hits"])
    

@app.route("/en/keyword", endpoint="keyword_index_en")
@app.route("/sv/nyckelord", endpoint="keyword_index_sv")
def keyword_index():
    data = karp_request("statlist?buckets=nyckelord.bucket")
    set_language_swith_link("keyword_index")
    return render_template('keywords.html', 
                            keywords = data['stat_table'], 
                            title = gettext("Keywords"))


@app.route("/en/keyword/<keyword>", endpoint="keyword_en")
@app.route("/sv/nyckelord/<keyword>", endpoint="keyword_sv")
def keyword(keyword=None):
    set_language_swith_link("keyword_index", keyword)
    hits = karp_query("extended||and|nyckelord.search|equals|%s" % (keyword))
    
    if hits['query']['hits']['total'] > 0:
    
        picture = None
        print app.config.root_path+'/static/images/keywords/'+keyword+'.jpg'
        if os.path.exists(app.config.root_path+'/static/images/keywords/'+keyword+'.jpg'):
            picture = keyword+'.jpg'
        
        return render_template('keyword.html', picture=picture, title=keyword, hits=hits["query"]["hits"])
    else:
        return render_template('page.html', content = 'not found')


@app.route("/en/article", endpoint="article_index_en")
@app.route("/sv/artikel", endpoint="article_index_sv")
def article_index():
    set_language_swith_link("article_index")
    return render_template('page.html', 
                            content = 'article index', 
                            title = 'Articles')


@app.route("/en/article/<id>", endpoint="article_en")
@app.route("/sv/artikel/<id>", endpoint="article_sv")
def article(id=None):
    data = karp_query("extended||and|id.search|equals|%s" % (id))
    set_language_swith_link("article_index", id)
    if data['query']['hits']['total'] == 1:
        return render_template('article.html', 
                                article = data['query']['hits']['hits'][0]['_source'])
    else:
        return render_template('page.html', content = 'not found')