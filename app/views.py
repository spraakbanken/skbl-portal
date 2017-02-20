from app import app, redirect, render_template, request, get_locale, get_language_swith_link, g

#redirect to specific language landing-page
@app.route('/')
def index():
    return redirect('/'+get_locale())

@app.route('/en', endpoint='index_en')
@app.route('/sv', endpoint='index_sv')
def welcome():
    get_language_swith_link("index")
    return render_template('page.html', content='skbl.se')

@app.route("/en/about", endpoint="about_en")
@app.route("/sv/om", endpoint="about_sv")
def about():
    get_language_swith_link("about")
    return render_template('page.html', content = g.language)
