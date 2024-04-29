"""Define different helper functions."""

import contextlib
import datetime
import json
import logging
import re
import sys
import urllib.parse
from urllib.request import Request, urlopen

import icu
import markdown
from flask import current_app, g, make_response, render_template, request, url_for
from flask_babel import gettext

from . import static_info

VONAV_LIST = ["von", "af", "av"]
VONAF_PATTERN_1 = re.compile(f'^({"|".join(VONAV_LIST)}) ')
VONAF_PATTERN_2 = re.compile(f'^({"|".join(VONAV_LIST)}) (.+)$')

logger = logging.getLogger(__name__)


def set_language_switch_link(route, fragment=None, lang=""):
    """Fix address and label for language switch button."""
    if not lang:
        lang = g.language
    if lang == "en":
        g.switch_language = {"url": url_for(f"views.{route}_sv"), "label": "Svenska"}
    else:
        g.switch_language = {"url": url_for(f"views.{route}_en"), "label": "English"}
    if fragment is not None:
        g.switch_language["url"] += f"/{fragment}"


def cache_name(pagename: str, lang: str = "") -> str:
    """Get page from cache."""
    if not lang:
        lang = "sv" if "sv" in request.url_rule.rule else "en"  # type: ignore[union-attr]
    return f"{pagename}_{lang}"


def karp_query(action, query, mode=None):
    """Generate query and send request to Karp."""
    if not mode:
        mode = current_app.config["KARP_MODE"]
    query["mode"] = mode
    query["resource"] = current_app.config["KARP_LEXICON"]
    if "size" not in query:
        query["size"] = current_app.config["RESULT_SIZE"]
    params = urllib.parse.urlencode(query)
    return karp_request(f"{action}?{params}")


def karp_request(action):
    """Send request to Karp backend."""
    q = Request(f'{current_app.config["KARP_BACKEND"]}/{action}')
    logger.debug("REQUEST: %s/%s", current_app.config["KARP_BACKEND"], action)
    if current_app.config.get("USE_AUTH", False):
        q.add_header("Authorization", f'Basic {current_app.config["KARP_AUTH_HASH"]}')
    response = urlopen(q).read()
    return json.loads(response.decode("UTF-8"))


def karp_fe_url():
    """Get URL for Karp frontend."""
    return current_app.config["KARP_FRONTEND"] + "/#?mode=" + current_app.config["KARP_MODE"]


def serve_static_page(page, title=""):
    """Serve static html."""
    set_language_switch_link(page)
    with current_app.open_resource(f"static/pages/{page}/{g.language}.html") as f:
        data = f.read().decode("UTF-8")

    return render_template("page_static.html", content=data, title=title)


def check_cache(page, lang=""):
    """Check if page is in cache.

    If the cache should not be used, return None.
    """
    if current_app.config["TEST"]:
        return None
    try:
        with g.mc_pool.reserve() as client:
            # Look for the page, return if found
            art = client.get(cache_name(page, lang))
            if art is not None:
                return art
    except Exception:
        # TODO what to do??
        pass

    # If nothing is found, return None
    return None


def set_cache(page, name="", no_hits=0):
    """Browser cache handling.

    Add header to the response.
    May also add the page to the memcache.
    """
    pagename = cache_name(name, lang="")
    if no_hits >= current_app.config["CACHE_HIT_LIMIT"]:
        try:
            with g.mc_pool.reserve() as client:
                client.set(pagename, page, time=current_app.config["LOW_CACHE_TIME"])
        except Exception:
            # TODO what to do??
            pass
    r = make_response(page)
    r.headers.set(
        "Cache-Control",
        f'public, max-age={current_app.config["BROWSER_CACHE_TIME"]}',
    )
    return r


def get_first_name(source):
    """Return the given name (first name)."""
    return re.sub("/", "", source["name"].get("firstname", "")).strip()


def format_names(source, fmt="strong"):
    """Return the given name (first name), and the formatted callingname (tilltalsnamnet)."""
    if fmt:
        return re.sub(
            "(.*)/(.+)/(.*)",
            rf"\1<{fmt}>\2</{fmt}>\3",
            source["name"].get("firstname", ""),
        )
    return re.sub("(.*)/(.+)/(.*)", r"\1\2\3", source["name"].get("firstname", ""))


def get_life_range(source):
    """Return the birth and death year from _source (as a tuple).

    Return empty strings if not available.
    """
    years = []
    for event in ["from", "to"]:
        if source["lifespan"].get(event):
            date = source["lifespan"][event].get("date", "")
            if date:
                date = date.get("comment", "")
            if "-" in date and not re.search("[a-zA-Z]", date):
                year = date[: date.find("-")]
            else:
                year = date
        else:
            year = ""
        years.append(year)

    return years[0], years[1]


def get_life_range_force(source):
    """Return the birth and death year from _source (as a tuple).

    Try to also parse non-dates like "ca. 1500-talet".
    Return -1, 1000000 if not available.
    """
    default_born = -1
    default_died = 1000000

    def convert(event, retval):
        if source["lifespan"].get(event):
            date = source["lifespan"][event].get("date", "")
            if date:
                date = date.get("comment", "")
                match = re.search(r".*(\d{4}).*", date)
                if match:
                    retval = int(match[1])
        return retval

    born = convert("from", default_born)
    dead = convert("to", default_died)

    # Sorting hack: if there is no birth year, set it to dead -100 (and vice versa)
    # to make is appear in a more reasonable position in the chronology
    if born == default_born and dead != default_died:
        born = dead - 100
    if dead == default_died and born != default_born:
        dead = born + 100

    return born, dead


def get_date(source):
    """Get birth and death date if available. Return empty strings otherwise."""
    dates = []
    for event in ["from", "to"]:
        if source["lifespan"][event].get("date"):
            date = source["lifespan"][event]["date"].get("comment", "")
        else:
            date = ""
        dates.append(date)

    return dates[0], dates[1]


def get_current_date():
    """Get the current date."""
    return datetime.datetime.strftime(datetime.datetime.now(), "%Y-%m-%d")


def markdown_html(text):
    """Convert markdown text to html."""
    return markdown.markdown(text)


def group_by_type(objlist, name):
    """Group objects by their type (=name), e.g. 'othernames'."""
    newdict = {}
    for obj in objlist:
        val = obj.get(name, "")
        key_sv = obj.get("type", "Övrigt")
        key_en = obj.get("type_eng", "Other")
        if key_sv not in newdict:
            newdict[key_sv] = (key_en, [])
        newdict[key_sv][1].append(val)
    return [
        {"type": key, "type_eng": val[0], name: ", ".join(val[1])}
        for key, val in newdict.items()
    ]


def group_alphabetical_without_vonaf(bucket, results):
    """Find starting letter without 'von', 'af' and 'av' from name.

    >>> results = []
    >>> drop_vonaf(["von Tupp"], results)
    >>> results
    [('T', 'von Tupp')]

    Args:
        bucket (str): _description_
        results (list[str]): _description_
    """
    name = VONAF_PATTERN_2.sub(r"\2", bucket[0])
    results.append((name[0].upper(), bucket))


def make_alphabetical_bucket(result, sortnames=False, lang="sv"):
    """Make a alphabetical bucket.

    Args:
        result (_type_): _description_
        sortnames (bool, optional): _description_. Defaults to False.
        lang (str, optional): _description_. Defaults to "sv".
    """
    return make_alphabetic(
        result, group_alphabetical_without_vonaf, sortnames=sortnames, lang=lang
    )


def rewrite_von(name):
    """Move 'von' and 'av' to end of name.

    >>> rewrite_von("von Tupp")
    'Tupp von'
    """
    return VONAF_PATTERN_2.sub(r"\2 \1", name)


def make_placenames(places, lang="sv"):  # noqa: D103
    def processname(hit, results):
        name = hit["name"].strip()
        results.append((name[0].upper(), (name, hit)))

    return make_alphabetic(places, processname, lang=lang)


def make_alphabetic(hits, processname, sortnames=False, lang="sv"):
    """Loop through hits, apply the function 'processname' on each object and then sort the result in alphabetical order.

    The function processname should append zero or more processed form of
    the object to the result list.
    This processed forms should be a pair (first_letter, result)
    where first_letter is the first_letter of each object (to sort on), and the result
    is what the html-template want e.g. a pair of (name, no_hits)
    """  # noqa: E501

    def fix_lastname(name):
        vonaf_pattern = re.compile(f'^({"|".join(VONAV_LIST)}) ')
        name = re.sub(vonaf_pattern, r"", name)
        return name.replace(" ", "z")

    results = []
    for hit in hits:
        processname(hit, results)

    letter_results = {}
    # Split the result into start letters
    for first_letter_init, result in results:
        if first_letter_init == "Ø":
            first_letter = "Ö"
        elif first_letter_init == "Æ":
            first_letter = "Ä"
        elif first_letter_init == "Ü":
            first_letter = "Y"
        else:
            first_letter = first_letter_init
        if lang == "en":
            if first_letter == "Ö":
                first_letter = "O"
            if first_letter in "ÄÅ":
                first_letter = "A"
        if first_letter not in letter_results:
            letter_results[first_letter] = [result]
        else:
            letter_results[first_letter].append(result)

    # Sort result dictionary alphabetically into list
    if lang == "en":
        collator = icu.Collator.createInstance(icu.Locale("en_EN.UTF-8"))
    else:
        collator = icu.Collator.createInstance(icu.Locale("sv_SE.UTF-8"))
    for _n, items in list(letter_results.items()):
        if sortnames:
            items.sort(key=lambda x: collator.getSortKey(f"{fix_lastname(x[0])} {x[1]}"))
        else:
            items.sort(key=lambda x: collator.getSortKey(x[0]))

    return sorted(letter_results.items(), key=lambda x: collator.getSortKey(x[0]))


def make_simplenamelist(hits, search):
    """Create a list with links to the entries url or _id.

    Sort entries with names matching the query higher.
    """
    results = []
    used = set()
    namefields = ["firstname", "lastname", "sortname"]
    search_terms = [st.lower() for st in search.split()]
    for hit in hits["hits"]:
        # score = sum(1 for field in hit["highlight"] if field.startswith("name."))
        hitname = hit["_source"]["name"]
        if score := sum(
            any(st in hitname.get(nf, "").lower() for st in search_terms) for nf in namefields
        ):
            name = join_name(hit["_source"], mk_bold=True)
            liferange = get_life_range(hit["_source"])
            subtitle = hit["_source"].get("subtitle", "")
            subtitle_eng = hit["_source"].get("subtitle_eng", "")
            subject_id = hit["_source"].get("url") or hit["_id"]
            results.append((-score, name, liferange, subtitle, subtitle_eng, subject_id))
            used.add(hit["_id"])
    return sorted(results), used


def make_namelist(hits, exclude=None, search=""):
    """Split hits into one list per first letter.

    Return only info necessary for listing of names.
    """
    if exclude is None:
        exclude = set()
    results = []
    first_letters = []  # List only containing letters in alphabetical order
    current_letterlist = []  # List containing entries starting with the same letter
    current_total = 0
    max_len = current_app.config["SEARCH_RESULT_SIZE"] - len(exclude) if search else None
    for hit in hits["hits"]:
        if hit["_id"] in exclude:
            continue
        # Separate names from linked names
        is_link = hit["_index"].startswith(current_app.config["SKBL_LINKS"])
        if is_link:
            name = hit["_source"]["name"].get("sortname", "")
            linked_name = join_name(hit["_source"])
        else:
            name = join_name(hit["_source"], mk_bold=True)
            linked_name = False

        liferange = get_life_range(hit["_source"])
        subtitle = hit["_source"].get("subtitle", "")
        subtitle_eng = hit["_source"].get("subtitle_eng", "")
        subject_id = hit["_source"].get("url") or hit["_id"]

        # Get first letter from sort[0]
        firstletter = hit["sort"][1].upper()
        if firstletter not in first_letters:
            if current_letterlist:
                results.append(current_letterlist)
                current_letterlist = []
            first_letters.append(firstletter)
        current_letterlist.append(
            (
                firstletter,
                is_link,
                name,
                linked_name,
                liferange,
                subtitle,
                subtitle_eng,
                subject_id,
            )
        )
        current_total += 1
        # Don't show more than SEARCH_RESULT_SIZE number of results
        if max_len and current_total >= max_len:
            break

    if current_letterlist:
        # Append last letterlist
        results.append(current_letterlist)

    return (first_letters, results)


def make_datelist(hits):
    """Extract information relevant for chronology list.

    (same as make_namelist but without letter splitting).
    """
    result = []
    for hit in hits:
        is_link = hit["_index"].startswith(current_app.config["SKBL_LINKS"])
        if is_link:
            name = hit["_source"]["name"].get("sortname", "")
            linked_name = join_name(hit["_source"])
        else:
            name = join_name(hit["_source"], mk_bold=True)
            linked_name = False

        liferange = get_life_range(hit["_source"])
        subtitle = hit["_source"].get("subtitle", "")
        subtitle_eng = hit["_source"].get("subtitle_eng", "")
        subject_id = hit["_source"].get("url") or hit["_id"]

        result.append(
            (is_link, name, linked_name, liferange, subtitle, subtitle_eng, subject_id)
        )
    return result


def join_name(source, mk_bold=False):
    """Retrieve and format name from source."""
    name = []
    lastname = source["name"].get("lastname", "")
    vonaf_pattern = re.compile(f'({" |".join(VONAV_LIST)} |)(.*)')
    match = re.search(vonaf_pattern, lastname)
    vonaf = match[1]
    if lastname := match[2]:
        if mk_bold:
            name.append(f"<strong>{lastname}</strong>,")
        else:
            name.append(f"{lastname},")
    if mk_bold:
        name.append(format_names(source, fmt="strong"))
    else:
        name.append(source["name"].get("firstname", ""))
    name.append(vonaf)
    return " ".join(name)


def sort_places(stat_table, route):
    """Translate place names and sort list."""
    # Work in progress! Waiting for translation list.
    # Or should this be part of the data instead??
    place_translations = {"Göteborg": "Gothenburg"}

    lang = "en" if "place" in route.rule else "sv"

    for d in stat_table:
        if lang == "en":
            d["display_name"] = place_translations.get(d["name"], d["name"])
        else:
            d["display_name"] = d["name"]

    stat_table.sort(key=lambda x: x.get("name").strip())
    return stat_table


def mk_links(text):
    """Fix display of links within an article text."""
    # TODO markdown should fix this itself
    with contextlib.suppress(Exception):
        text = re.sub(r"\[\]\((.*?)\)", r"[\1](\1)", text)
        for link in re.findall(r"\]\((.*?)\)", text):
            text = re.sub(
                rf"\({link}\)",
                "({})".format(url_for(f"views.article_index_{g.language}", search=link)),
                text,
            )
    return text


def unescape(text):
    """Unescape some html chars."""
    text = re.sub("&gt;", r">", text)
    return re.sub("&apos;", r"'", text)


def aggregate_by_type(items, use_markdown=False):  # noqa: D103
    if not isinstance(items, list):
        items = [items]
    types = {}
    for item in items:
        if "type" in item and (t := item["type"]):
            if t not in types:
                types[t] = []
            if use_markdown and "description" in item:
                item["description"] = markdown_html(item["description"])
                item["description_eng"] = markdown_html(item.get("description_eng", ""))
            types[t].append(item)
    return list(types.items())


def collapse_kids(source):  # noqa: D103
    unknown_kids = 0
    for relation in source.get("relation", []):
        if relation.get("type") == "Barn" and len(list(relation.keys())) == 1:
            unknown_kids += 1
            relation["hide"] = True
    if unknown_kids:
        source["collapsedrelation"] = [{"type": "Barn", "count": unknown_kids}]


def make_placelist(hits, placename, _lat, _lon):  # noqa: D103
    grouped_results = {}
    for hit in hits["hits"]:
        source = hit["_source"]
        hit["url"] = source.get("url") or hit["_id"]
        placelocations = {
            gettext("Residence"): source.get("places", []),
            gettext("Place of activity"): source.get("occupation", []),
            gettext("Place of education"): source.get("education", []),
            gettext("Contacts"): source.get("contact", []),
            gettext("Birthplace"): [source.get("lifespan", {}).get("from", {})],
            gettext("Place of death"): [source.get("lifespan", {}).get("to", {})],
        }

        for ptype, places in list(placelocations.items()):
            names = {
                place.get("place", {}).get("place", "").strip(): place.get("place", {}).get(
                    "pin", {}
                )
                for place in places
            }
            # Check if the name and the lat, lon is correct
            # (We can't ask karp of this, since it would be a nested query)
            if placename in names:
                # Coordinates! If coordinates are used, uncomment the two lines below
                # if names[placename].get("lat") == float(lat)\
                #    and names[placename].get("lon") == float(lon):
                if ptype not in grouped_results:
                    grouped_results[ptype] = []
                grouped_results[ptype].append((join_name(hit["_source"], mk_bold=True), hit))
                # else:
                #     # These two lines should be removed, but are kept for debugging
                #     if "Fel" not in grouped_results: grouped_results["Fel"] = []
                #     grouped_results["Fel"].append((join_name(source), hit))

    # Sort result dictionary alphabetically into list
    collator = icu.Collator.createInstance(icu.Locale("sv_SE.UTF-8"))
    for _n, items in list(grouped_results.items()):
        items.sort(key=lambda x: collator.getSortKey(x[0]))
    return sorted(grouped_results.items(), key=lambda x: collator.getSortKey(x[0]))


def is_email_address_valid(email):
    """Validate the email address using a regex.

    It may not include any whitespaces, has exactly one "@" and at least one "." after the "@".
    """
    return False if " " in email else bool(re.match(r"[^@]+@[^@]+\.[^@]+", email))


def is_ascii(s):
    """Check if s contains of ASCII-characters only."""
    return all(ord(c) < 128 for c in s)  # noqa: PLR2004


def get_lang_text(json_swe, json_eng, ui_lang):
    """Get text in correct language if available."""
    return json_eng or json_swe if ui_lang == "en" else json_swe


def get_shorttext(text):
    """Get the initial 200 characters of text. Remove HTML and line breaks."""
    shorttext = re.sub(r"<.*?>|\n|\t", " ", text)
    shorttext = shorttext.strip()
    shorttext = re.sub(r"  ", " ", shorttext)
    return shorttext[:200]


def get_org_name(organisation):
    """Get short name for organisation (--> org.)."""
    if organisation.endswith(("organisation", "organization")):
        return f"{organisation[:-9]}."
    return organisation


def lowersorted(xs):
    """Sort case-insentitively."""
    return sorted(xs, key=lambda x: x[0].lower())


def get_infotext(text, rule):
    """Get infotext in correct language with Swedish as fallback.

    text = key in the infotext dict
    rule = request.url_rule.rule
    """
    textobj = static_info.infotexter.get(text)
    if "sv" in rule:
        return textobj.get("sv")
    return textobj.get("en", textobj.get("sv"))


def log(data, msg=""):
    """Log data to stderr."""
    if msg:
        sys.stderr.write("\n" + msg + ": " + str(data) + "\n")
    else:
        sys.stderr.write("\n" + str(data) + "\n")


def swedish_translator(firstname, lastname):
    """Check if 'firstname lastname' is a Swedish translator."""
    swedish_translators = ["Linnea Åshede"]

    name = f"{firstname} {lastname}"
    return name in swedish_translators


def get_littb_id(skbl_url):
    """Get Litteraturbanken ID for an article if available."""
    if not skbl_url:
        return None
    littb_url = (
        "https://litteraturbanken.se/api/list_all/author?filter_and={%22wikidata.skbl_link%22:%20%22"
        + skbl_url
        + "%22}&include=authorid"
    )
    try:
        # Fake the user agent to avoid getting a 403
        r = Request(
            littb_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36"
            },
        )
        contents = urlopen(r).read()
    except Exception as e:
        logger.error("Could not open URL %s. Error: %s", littb_url, e)
        return None
    resp = json.loads(contents)
    return resp["data"][0]["authorid"] if resp.get("data") else None
