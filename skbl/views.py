"""Define all available routes."""

import logging
import re
import urllib.error
import urllib.parse
import urllib.request

import icu
from flask import (
    Blueprint,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_babel import gettext

from . import computeviews, helpers, static_info
from .authors import authors_dict

bp = Blueprint("views", __name__)

logger = logging.getLogger(__name__)


@bp.route("/")
def index():
    """Redirect to language specific landing-page."""
    return redirect(f"/{g.language}")


@bp.errorhandler(404)
def page_not_found(e):
    """Generate view for 404."""
    helpers.set_language_switch_link("index")
    logger.error("Error: '%s' Info: %s", str(e), repr(e))
    return render_template("page.html", content=gettext("Contents could not be found!")), 404


@bp.route("/en", endpoint="index_en")
@bp.route("/sv", endpoint="index_sv")
def start():
    """Generate view for landing page."""
    page = helpers.check_cache("start")
    if page is not None:
        return page
    infotext = helpers.get_infotext("start", request.url_rule.rule)
    helpers.set_language_switch_link("index")
    page = render_template(
        "start.html",
        title="Svenskt kvinnobiografiskt lexikon",
        infotext=infotext,
        description=helpers.get_shorttext(infotext),
    )
    return helpers.set_cache(page)


@bp.route("/en/about-skbl", endpoint="about-skbl_en")
@bp.route("/sv/om-skbl", endpoint="about-skbl_sv")
def about_skbl():
    """Generate view for about page."""
    page = helpers.serve_static_page("about-skbl", gettext("About SKBL"))
    return helpers.set_cache(page)


@bp.route("/en/biographies", endpoint="biographies_en")
@bp.route("/sv/biografiska-verk", endpoint="biographies_sv")
def biographies():
    """Generate view for biographies page."""
    page = helpers.serve_static_page("biographies", gettext("Older biographies"))
    return helpers.set_cache(page)


@bp.route("/en/quiz", endpoint="quiz_en")
@bp.route("/sv/quiz", endpoint="quiz_sv")
def quiz():
    """Generate view for 'Quiz'."""
    page = helpers.check_cache("quiz")
    if page is not None:
        return page
    infotext = helpers.get_infotext("quiz", request.url_rule.rule)
    helpers.set_language_switch_link("quiz")
    page = render_template("quiz.html", infotext=infotext, title=gettext("Quiz"))
    return helpers.set_cache(page)


@bp.route("/en/contact", endpoint="contact_en")
@bp.route("/sv/kontakt", endpoint="contact_sv")
def contact():
    """Generate view for contact form."""
    helpers.set_language_switch_link("contact")

    # Set suggestion checkbox
    mode = "suggestion" if request.args.get("suggest") == "true" else "other"
    page = render_template(
        "contact_active.html",
        title=gettext("Contact"),
        headline=gettext("Contact SKBL"),
        form_data={},
        mode=mode,
    )
    return helpers.set_cache(page)


# @bp.route("/en/contact/", methods=["POST"], endpoint="submitted_en")
# @bp.route("/sv/kontakt/", methods=["POST"], endpoint="submitted_sv")
# def submit_contact_form():
#     """Generate view for submitted contact form."""
#     return helpers.set_cache(computeviews.compute_contact_form())


@bp.route("/en/map", endpoint="map_en")
@bp.route("/sv/karta", endpoint="map_sv")
def show_map():
    """Generate view for the map."""
    art = computeviews.compute_map()
    return helpers.set_cache(art)


@bp.route("/en/chronology", endpoint="chronology_index_en")
@bp.route("/sv/kronologi", endpoint="chronology_index_sv")
def chronology_index():
    """Generate view for chronology and redirect to default time range."""
    return redirect(url_for(f"views.chronology_{g.language}", years="1400-1800"))


@bp.route("/en/chronology/<years>", endpoint="chronology_en")
@bp.route("/sv/kronologi/<years>", endpoint="chronology_sv")
def chronology(years=""):
    """Generate view for chronology."""
    startyear = years.split("-")[0]
    endyear = years.split("-")[1]
    # Todo: catch error if year has wrong format?

    infotext = helpers.get_infotext("chronology", request.url_rule.rule)

    lang = g.language
    if lang == "en":
        g.switch_language = {
            "url": url_for("views.chronology_sv", years=years),
            "label": "Svenska",
        }
    else:
        g.switch_language = {
            "url": url_for("views.chronology_en", years=years),
            "label": "English",
        }

    show = "name,url,undertitel,lifespan,undertitel_eng"

    # Get minientry for all women
    selection = helpers.karp_query(
        "minientry",
        {"q": "extended||and|namn|exists", "show": show, "sort": "fodd_comment.bucket"},
        mode=current_app.config["SKBL_LINKS"],
    )

    # Add birth and death years
    # convert non-dates like "ca. 1500-talet"
    # sort resulting list by year
    born_years = set()
    died_years = set()
    for woman in selection["hits"]["hits"]:
        dates = helpers.get_life_range_force(woman["_source"])
        woman["_source"]["lifespan_simple"] = dates
        born_years.add(dates[0])
        died_years.add(dates[1])
    results = sorted(selection["hits"]["hits"], key=lambda i: i["_source"]["lifespan_simple"])

    # Get boundaries for chronology
    first_born = min(list(born_years))
    last_died = max(list(died_years))

    # Remove all women who have not been living in the selected interval
    new_results = []
    for result in results:
        dates = result["_source"]["lifespan_simple"]
        born_in_interval = int(startyear) <= dates[0] <= int(endyear)
        died_in_interval = int(startyear) <= dates[1] <= int(endyear)
        if born_in_interval or died_in_interval:
            new_results.append(result)

    page = render_template(
        "chronology.html",
        title=gettext("Chronology"),
        headline=gettext("Chronology"),
        infotext=infotext,
        min=first_born,
        max=last_died,
        default_low=startyear,
        default_high=endyear,
        hits=new_results,
        lang=lang,
    )
    return helpers.set_cache(page)


@bp.route("/en/search", endpoint="search_en")
@bp.route("/sv/sok", endpoint="search_sv")
def search():
    """Generate view for search results."""
    helpers.set_language_switch_link("search")
    search = request.args.get("q", "")
    pagename = f"search{urllib.parse.quote(search)}"

    page = helpers.check_cache(pagename)
    if page is not None:
        return page

    advanced_search_text = ""
    if search:
        show = (
            "name,url,undertitel,undertitel_eng,lifespan,platspinlat.bucket,platspinlon.bucket"
        )
        karp_q = {
            "highlight": True,
            "size": current_app.config["RESULT_SIZE"],
            "show": show,
        }
        if "*" in search:
            search = re.sub(r"(?<!\.)\*", ".*", search)
            karp_q["q"] = f"extended||and|anything|regexp|{search}"
        else:
            karp_q["q"] = f"extended||and|anything|contains|{search}"

        mode = current_app.config["KARP_MODE"]
        data = helpers.karp_query("minientry", karp_q, mode=mode)
        with current_app.open_resource(f"static/pages/advanced-search/{g.language}.html") as f:
            advanced_search_text = f.read().decode("UTF-8")
        karp_url = (
            "https://spraakbanken.gu.se/karp/#?mode="
            + mode
            + "&advanced=false&hpp=25&extended=and%7Cnamn%7Cequals%7C&searchTab=simple&page=1&search=simple%7C%7C"  # noqa: E501
            + search
        )
    else:
        data = {"hits": {"total": 0, "hits": []}}
        karp_url = ""
        search = "\u200b"

    number_hits = min(current_app.config["SEARCH_RESULT_SIZE"], data["hits"]["total"])

    t = render_template(
        "list.html",
        headline="",
        subheadline=gettext("Hits for '%s'") % search,
        hits_name=data["hits"],
        hits=data["hits"],
        advanced_search_text=advanced_search_text,
        search=search,
        alphabetic=True,
        karp_url=karp_url,
        number_hits=number_hits,
        more=data["hits"]["total"] > current_app.config["SEARCH_RESULT_SIZE"],
        show_lang_switch=False,
    )

    return helpers.set_cache(t, name=pagename, no_hits=data["hits"]["total"])


@bp.route("/en/place", endpoint="place_index_en")
@bp.route("/sv/ort", endpoint="place_index_sv")
def place_index():
    """Generate view for places list."""
    return helpers.set_cache(computeviews.compute_place())


@bp.route("/en/place/<place>", endpoint="place_en")
@bp.route("/sv/ort/<place>", endpoint="place_sv")
def place(place=None):
    """Generate view for one place."""
    pagename = urllib.parse.quote(f"place_{place}")
    art = helpers.check_cache(pagename)
    if art is not None:
        return art
    lat = request.args.get("lat")
    lon = request.args.get("lon")
    helpers.set_language_switch_link("place_index", place)
    hits = helpers.karp_query("query", {"q": f"extended||and|plats.searchraw|equals|{place}"})
    no_hits = hits["hits"]["total"]
    if no_hits > 0:
        page = render_template(
            "placelist.html",
            title=place,
            lat=lat,
            lon=lon,
            headline=place,
            hits=hits["hits"],
        )
    else:
        page = render_template("page.html", content=gettext("Contents could not be found!"))
    return helpers.set_cache(page, name=pagename, no_hits=no_hits)


@bp.route("/en/organisation", endpoint="organisation_index_en")
@bp.route("/sv/organisation", endpoint="organisation_index_sv")
def organisation_index():
    """Generate view for organisations list."""
    return helpers.set_cache(computeviews.compute_organisation())


@bp.route("/en/organisation/<result>", endpoint="organisation_en")
@bp.route("/sv/organisation/<result>", endpoint="organisation_sv")
def organisation(result=None):
    """Generate view for one organisation."""
    title = request.args.get("title")

    lang = "sv" if "sv" in request.url_rule.rule else "en"
    page = computeviews.searchresult(
        result,
        "organisation",
        "id",
        "organisations",
        title=title,
        lang=lang,
        show_lang_switch=False,
    )
    return helpers.set_cache(page)


@bp.route("/en/activity", endpoint="activity_index_en")
@bp.route("/sv/verksamhet", endpoint="activity_index_sv")
def activity_index():
    """Generate view for activities list."""
    return helpers.set_cache(computeviews.compute_activity())


@bp.route("/en/activity/<result>", endpoint="activity_en")
@bp.route("/sv/verksamhet/<result>", endpoint="activity_sv")
def activity(result=None):
    """Generate view for one activity."""
    page = computeviews.searchresult(
        result,
        name="activity",
        searchfield="verksamhetstext",
        imagefolder="activities",
        title=result,
    )
    return helpers.set_cache(page)


@bp.route("/en/keyword", endpoint="keyword_index_en")
@bp.route("/sv/nyckelord", endpoint="keyword_index_sv")
def keyword_index():
    """Generate view for keywords list."""
    infotext = helpers.get_infotext("keyword", request.url_rule.rule)
    helpers.set_language_switch_link("keyword_index")
    lang = "sv" if "sv" in request.url_rule.rule else "en"
    pagename = "keyword"
    art = helpers.check_cache(pagename, lang=lang)
    if art is not None:
        return art

    if lang == "en":
        reference_list = []
        queryfield = "nyckelord_eng"
    else:
        # Fix list with references to be inserted in results
        reference_list = static_info.keywords_reference_list
        [ref.append("reference") for ref in reference_list]
        queryfield = "nyckelord"

    art = computeviews.bucketcall(
        queryfield=queryfield,
        name="keyword",
        title="Keywords",
        infotext=infotext,
        alphabetical=True,
        insert_entries=reference_list,
        description=helpers.get_shorttext(infotext),
    )
    return helpers.set_cache(
        art, name=pagename, lang=lang, no_hits=current_app.config["CACHE_HIT_LIMIT"]
    )


@bp.route("/en/keyword/<result>", endpoint="keyword_en")
@bp.route("/sv/nyckelord/<result>", endpoint="keyword_sv")
def keyword(result=None):
    """Generate view for one keyword."""
    lang = "sv" if "sv" in request.url_rule.rule else "en"
    if lang == "en":
        page = computeviews.searchresult(
            result,
            "keyword",
            "nyckelord_eng",
            "keywords",
            lang=lang,
            show_lang_switch=False,
        )
    else:
        page = computeviews.searchresult(
            result,
            "keyword",
            "nyckelord",
            "keywords",
            lang=lang,
            show_lang_switch=False,
        )
    # The page is memcached by search results
    return helpers.set_cache(page)


# @bp.route("/en/author_presentations", endpoint="author_presentations_en")
# @bp.route("/sv/forfattar_presentationer", endpoint="author_presentations_sv")
# def author_presentations():
#     """Generate view for author presentations (just for testing purposes)."""
#     helpers.set_language_switch_link("author_presentations")
#     authorinfo = []
#     keylist = list(authors_dict.keys())
#     keylist.sort(key=lambda k: k.split()[1])
#     for key in keylist:
#         if authors_dict[key].get("publications"):
#             authors_dict[key]["publications"] = [helpers.markdown_html(i) for i in authors_dict[key].get("publications")]  # noqa: E501
#         if authors_dict[key].get("sv"):
#             authors_dict[key]["sv"] = helpers.markdown_html(authors_dict[key].get("sv"))
#         authorinfo.append((key, authors_dict[key]))
#     page = render_template("author_presentations.html", authorinfo=authorinfo, title="Authors")
#     return helpers.set_cache(page)


@bp.route("/en/articleauthor", endpoint="articleauthor_index_en")
@bp.route("/sv/artikelforfattare", endpoint="articleauthor_index_sv")
def authors():
    """Generate view for authors list."""
    infotext = helpers.get_infotext("articleauthor", request.url_rule.rule)
    helpers.set_language_switch_link("articleauthor_index")
    return helpers.set_cache(
        computeviews.compute_artikelforfattare(
            infotext=infotext, description=helpers.get_shorttext(infotext)
        )
    )


@bp.route("/en/articleauthor/<result>", endpoint="articleauthor_en")
@bp.route("/sv/artikelforfattare/<result>", endpoint="articleauthor_sv")
def author(result=None):
    """Generate view for one author."""
    helpers.set_language_switch_link("articleauthor_index")
    rule = request.url_rule
    lang = "sv" if "sv" in rule.rule else "en"
    # Try to get authorinfo in correct language (with Swedish as fallback)
    firstname = result.split(", ")[-1].strip()
    lastname = result.split(", ")[0].strip()
    authorinfo = authors_dict.get(f"{firstname} {lastname}")
    if authorinfo:
        authorinfo = [
            helpers.markdown_html(authorinfo.get(lang, authorinfo.get("sv"))),
            [helpers.markdown_html(i) for i in authorinfo.get("publications", [])],
        ]
    query = f"extended||and|artikel_forfattare_fornamn.lowerbucket|equals|{firstname}||and|artikel_forfattare_efternamn.lowerbucket|equals|{lastname}"  # noqa: E501
    page = computeviews.searchresult(
        result,
        name="articleauthor",
        query=query,
        imagefolder="authors",
        authorinfo=authorinfo,
        show_lang_switch=False,
    )
    return helpers.set_cache(page)


@bp.route("/en/article", endpoint="article_index_en")
@bp.route("/sv/artikel", endpoint="article_index_sv")
def article_index(search=None):
    """Generate view for A-Z list."""
    helpers.set_language_switch_link("article_index")
    # Search is only used by links in article text
    search = search or request.args.get("search")
    if search is not None:
        data, id = find_link(search)  # noqa: A001
        if id:
            # Only one hit is found, redirect to that page
            page = redirect(url_for(f"views.article_{g.language}", id=id))
            return helpers.set_cache(page)
        # elif data["hits"]["total"] > 1:
        if len(data["hits"]["hits"]) > 1:
            # More than one hit is found, redirect to a listing
            page = redirect(url_for(f"views.search_{g.language}", q=search))
            return helpers.set_cache(page)
        # No hits are found redirect to a "not found" page
        return render_template("page.html", content=gettext("Contents could not be found!")), 404

    art = computeviews.compute_article()
    return helpers.set_cache(art)


@bp.route("/en/article/<id>", endpoint="article_en")
@bp.route("/sv/artikel/<id>", endpoint="article_sv")
def article(id=None):  # noqa: A002
    """Generate view for one article."""
    rule = request.url_rule
    lang = "sv" if "sv" in rule.rule else "en"
    pagename = f"article_{id}"
    logger.debug("pagename=%s", pagename)
    page = helpers.check_cache(pagename, lang=lang)
    if page is not None:
        logger.debug("found pagename in cache. page=%s", page)
        return page
    logger.info("Did not find pagename=%s in cache, generating", pagename)
    data = helpers.karp_query("query", {"q": f"extended||and|url|equals|{id}"})
    # if data["hits"]["total"] == 0:
    if len(data["hits"]["hits"]) == 0:
        logger.info("karp_query included no hits, search for 'id.search'")
        data = helpers.karp_query("query", {"q": f"extended||and|id.search|equals|{id}"})
    helpers.set_language_switch_link("article_index", id)
    page = show_article(data, lang)
    # logger.debug("page=%s", page)
    logger.debug("set cache")
    return helpers.set_cache(page, name=pagename, lang=lang, no_hits=1)


@bp.route("/en/article/EmptyArticle", endpoint="article_empty_en")
@bp.route("/sv/artikel/TomArtikel", endpoint="article_empty_sv")
def empty_article():
    """Generate a view for a non-existing article."""
    helpers.set_language_switch_link("article_empty")
    rule = request.url_rule
    if "sv" in rule.rule:
        content = """Den här kvinnan saknas än så länge."""
    else:
        content = """This entry does not exist yet."""
    page = render_template("page.html", content=content)
    return helpers.set_cache(page)


def find_link(searchstring):
    """Find an article based on ISNI or name."""
    if re.search(r"^[0-9 ]*X?$", searchstring):
        searchstring = searchstring.replace(" ", "")
        data = helpers.karp_query(
            "query", {"q": f"extended||and|swoid.search|equals|{searchstring}"}
        )
    else:
        parts = searchstring.split(" ")
        if (
            "," in searchstring or len(parts) == 1
        ):  # When there is only a first name (a queen or so)
            # Case 1: "Margareta"
            # Case 2: "Margareta, drottning"
            firstname = parts[0] if len(parts) == 1 else searchstring
            data = helpers.karp_query(
                "query", {"q": f"extended||and|fornamn.search|contains|{firstname}"}
            )
        else:
            fornamn = " ".join(parts[0:-1])
            prefix = ""
            last_fornamn = fornamn.split(" ")[-1]
            if last_fornamn in helpers.VONAV_LIST:
                fornamn = " ".join(fornamn.split(" ")[0:-1])
                prefix = last_fornamn + " "
            efternamn = prefix + parts[-1]
            data = helpers.karp_query(
                "query",
                {
                    "q": f"extended||and|fornamn.search|contains|{fornamn}||and|efternamn.search|contains|{efternamn}"  # noqa: E501
                },
            )
    # The expected case: only one hit is found
    # if data["hits"]["total"] == 1:
    if len(data["hits"]["hits"]) == 1:
        url = data["hits"]["hits"][0]["_source"].get("url")
        es_id = data["hits"]["hits"][0]["_id"]
        return data, (url or es_id)
        # Otherwise just return the data
    return data, ""


def show_article(data, lang="sv"):
    """Prepare data for article view (helper function)."""
    # if len(data["hits"]["hits"]) == 1:
    if len(data["hits"]["hits"]) <= 0:
        logger.debug("data['hits']['hits']=%s", data["hits"]["hits"])
        return render_template("page.html", content=gettext("Contents could not be found!")), 404
    source = data["hits"]["hits"][0]["_source"]
    source["url"] = source.get("url") or data["query"]["hits"]["hits"][0]["_id"]
    source["es_id"] = data["hits"]["hits"][0]["_id"]

    # Print html for the names with the calling name and last name in bold
    formatted_names = helpers.format_names(source, "b")
    source["showname"] = f"{formatted_names} <b>{source['name'].get('lastname', '')}</b>"
    title = f"{helpers.format_names(source, '')} {source['name'].get('lastname', '')}"
    if source.get("text"):
        source["text"] = helpers.markdown_html(
            helpers.unescape(helpers.mk_links(source["text"]))
        )
    if source.get("text_eng"):
        source["text_eng"] = helpers.markdown_html(
            helpers.unescape(helpers.mk_links(source["text_eng"]))
        )

    # Extract linked names from source
    source["linked_names"] = find_linked_names(
        source.get("othernames", {}), source.get("showname")
    )
    source["othernames"] = helpers.group_by_type(source.get("othernames", {}), "name")

    helpers.collapse_kids(source)
    if "source" in source:
        source["source"] = helpers.aggregate_by_type(source["source"], use_markdown=True)
    if "furtherreference" in source:
        source["furtherreference"] = helpers.aggregate_by_type(
            source["furtherreference"], use_markdown=True
        )
    if not isinstance(source["article_author"], list):
        source["article_author"] = [source["article_author"]]

    # Set description for meta data
    if lang == "sv":
        description = helpers.get_shorttext(source.get("text", ""))
    else:
        description = helpers.get_shorttext(source.get("text_eng", source.get("text", "")))

    image = source["portrait"][0].get("url", "") if source.get("portrait") else ""

    # Sort keywords alphabetically
    kw = source.get("keyword", [])
    collator = icu.Collator.createInstance(icu.Locale("sv_SE.UTF-8"))
    kw.sort(key=collator.getSortKey)

    under_development = source.get("skbl_status") == "Under utveckling"

    littb_url = helpers.get_littb_id(source.get("url"))

    logger.debug(
        "render article_id=%s article_url=%s title=%s",
        source["es_id"],
        source["url"],
        title,
    )
    return render_template(
        "article.html",
        article=source,
        article_id=source["es_id"],
        article_url=source["url"],
        title=title,
        description=description,
        image=image,
        under_development=under_development,
        littb_id=littb_url,
    )


def find_linked_names(othernames, showname):
    """Find and format linked names."""
    linked_names = []
    for item in othernames:
        if item.get("mk_link") is True:
            name = fix_name_order(item.get("name"))
            # Do not add linked name if all of its parts occur in showname
            if any(i for i in name.split() if i not in showname):
                linked_names.append(name)
    return ", ".join(linked_names)


def fix_name_order(name):
    """Lastname, Firstname --> Firstname Lastname."""
    nameparts = name.split(", ")
    if len(nameparts) == 1:
        return nameparts[0]
    if len(nameparts) == 2:  # noqa: PLR2004
        return f"{nameparts[1]} {nameparts[0]}"
    if len(nameparts) == 3:  # noqa: PLR2004
        return f"{nameparts[2]} {nameparts[1]} {nameparts[0]}"
    return None


@bp.route("/en/award", endpoint="award_index_en")
@bp.route("/sv/pris", endpoint="award_index_sv")
def award_index():
    """List all awards.

    There are no links to this page, but might be wanted later on
    Exists only to support award/<result> below
    """
    helpers.set_language_switch_link("award_index")
    pagename = "award"
    art = helpers.check_cache(pagename)
    if art is not None:
        return art
    art = computeviews.bucketcall(
        queryfield="prisbeskrivning", name="award", title="Award", infotext=""
    )
    return helpers.set_cache(art, name=pagename, no_hits=current_app.config["CACHE_HIT_LIMIT"])


@bp.route("/en/award/<result>", endpoint="award_en")
@bp.route("/sv/pris/<result>", endpoint="award_sv")
def award(result=None):
    """Search for award."""
    page = computeviews.searchresult(
        result,
        name="award",
        searchfield="prisbeskrivning",
        imagefolder="award",
        searchtype="equals",
    )
    return helpers.set_cache(page)


@bp.route("/en/education_institution", endpoint="institution_index_en")
@bp.route("/sv/utbildningsinstitution", endpoint="institution_index_sv")
def institution_index():
    """List all education institutions.

    There are no links to this page, but might be wanted later on
    Exists only to support institution/<result> below
    """
    helpers.set_language_switch_link("institution_index")
    page = computeviews.bucketcall(
        queryfield="utbildningsinstitution",
        name="award",
        title="Institution",
        infotext="",
    )
    return helpers.set_cache(page)


@bp.route("/en/education_institution/<result>", endpoint="institution_en")
@bp.route("/sv/utbildningsinstitution/<result>", endpoint="institution_sv")
def institution(result=None):
    """Search for education institution."""
    page = computeviews.searchresult(
        result, name="institution", searchfield="utbildningsinstitution", title=result
    )
    return helpers.set_cache(page)


@bp.route("/en/article/<id>.json", endpoint="article_json_en")
@bp.route("/sv/artikel/<id>.json", endpoint="article_json_sv")
def article_json(id=None):  # noqa: A002
    """Get article in JSON."""
    data = helpers.karp_query("query", {"q": f"extended||and|url|equals|{id}"})
    # if data["hits"]["total"] == 1:
    if len(data["hits"]["hits"]) == 1:
        page = jsonify(data["hits"]["hits"][0]["_source"])
        return helpers.set_cache(page)
    data = helpers.karp_query("query", {"q": f"extended||and|id.search|equals|{id}"})
    # if data["hits"]["total"] == 1:
    if len(data["hits"]["hits"]) == 1:
        page = jsonify(data["hits"]["hits"][0]["_source"])
        return helpers.set_cache(page)
    return None


# ### Cache handling ###
@bp.route("/emptycache")
def emptycache():
    """Empty the cache.

    Users with write permissions to skbl may use this call.
    """
    emptied = False
    try:
        emptied = computeviews.compute_emptycache(
            ["article", "activity", "organisation", "place", "author"]
        )
    except Exception:
        emptied = False
        # return jsonify({"error": "%s" % e})
    return jsonify({"cached_emptied": emptied})


@bp.route("/cachestats")
def cachestats():
    """Show stats of the cache."""
    with g.mc_pool.reserve() as client:
        return jsonify({"cached_stats": client.get_stats()})


@bp.route("/en/fillcache", endpoint="fillcache_en")
@bp.route("/sv/fillcache", endpoint="fillcache_sv")
def fillcache():
    """Refill the cache (~ touch all pages).

    This request will take some seconds, users may want to make an
    asynchronous call. Compute new pages
    """
    urls = {
        "activity": ("en/activity", "sv/verksamhet"),
        "article": ("en/article", "sv/artikel"),
        "organisation": ("en/organisation", "sv/organisation"),
        "place": ("en/place", "sv/ort"),
        "forfattare": ("en/articleauthor/<result>", "sv/artikelforfattare/<result>"),
    }
    lang = "sv" if "sv" in request.url_rule.rule else "en"
    lix = 0 if lang == "eng" else 1
    try:
        computeviews.compute_article(cache=False, url=request.url_root + urls["article"][lix])
    except Exception:
        logger.exception("Error computing article")
        raise
    try:
        computeviews.compute_activity(cache=False, url=request.url_root + urls["activity"][lix])
    except Exception:
        logger.exception("Error computing activity")
        raise
    try:
        computeviews.compute_organisation(
            cache=False, url=request.url_root + urls["organisation"][lix]
        )
    except Exception:
        logger.exception("Error computing organisation")
        raise
    try:
        computeviews.compute_place(cache=False, url=request.url_root + urls["place"][lix])
    except Exception:
        logger.exception("Error computing place")
        raise
    try:
        computeviews.compute_artikelforfattare(
            cache=False, url=request.url_root + urls["forfattare"][lix]
        )
    except Exception:
        logger.exception("Error computing artikelforfattare")
        raise
    try:
        # Copy the pages to the backup fields
        computeviews.copytobackup(
            ["article", "activity", "organisation", "place", "author"], lang
        )
    except Exception:
        logger.exception("Error copytobackup")
        raise
    return jsonify({"cache_filled": True, "cached_language": lang})


@bp.route("/mcpoolid")
def mcpoolid():
    """Show memcached pool ID."""
    return jsonify({"id": id(g.mc_pool)})
