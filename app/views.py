from app import app, redirect, render_template, request, get_locale, set_language_swith_link, g

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
    set_language_swith_link("about-skbl")
    return render_template('page.html', content = g.language)


@app.route("/en/about-us", endpoint="about-us_en")
@app.route("/sv/om-oss", endpoint="about-us_sv")
def about_us():
    set_language_swith_link("about-us")
    return render_template('page.html', content = g.language)

@app.route("/en/contact", endpoint="contact_en")
@app.route("/sv/kontakt", endpoint="contact_sv")
def about_us():
    set_language_swith_link("about-us")
    return render_template('page.html', content = g.language)