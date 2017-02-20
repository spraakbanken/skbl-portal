from app import app, redirect, render_template, request, get_locale, set_language_swith_link, g, serve_static_page

#redirect to specific language landing-page
@app.route('/')
def index():
    return redirect('/'+get_locale())

@app.route('/en', endpoint='index_en')
@app.route('/sv', endpoint='index_sv')
def welcome():
    set_language_swith_link("index")
    return render_template('page.html', content='skbl.se')

@app.route("/en/about-skbl", endpoint="about-skbl_en")
@app.route("/sv/om-skbl", endpoint="about-skbl_sv")
def about_skbl():
    return serve_static_page("about-skbl")

@app.route("/en/about-us", endpoint="about-us_en")
@app.route("/sv/om-oss", endpoint="about-us_sv")
def about_us():
    return serve_static_page("about-us")

@app.route("/en/contact", endpoint="contact_en")
@app.route("/sv/kontakt", endpoint="contact_sv")
def contact():
    return serve_static_page("contact")


@app.route("/en/keyword", endpoint="keyword_en")
@app.route("/sv/nyckelord", endpoint="keyword_sv")
@app.route("/en/keyword/<keyword>", endpoint="keyword_en")
@app.route("/sv/nyckelord/<keyword>", endpoint="keyword_sv")
def keyword(keyword=None):
    set_language_swith_link("keyword", keyword)
    return render_template('page.html', content = keyword)