"""Define helper functions used to compute the different views."""

import contextlib
import json
import operator
import os.path
import smtplib
import urllib.parse
from collections import defaultdict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from hashlib import md5
from urllib.request import urlopen

from flask import current_app, g, render_template, request
from flask_babel import gettext

from . import helpers, static_info


def getcache(page, lang, usecache):
    """Get cached page.

    Check if the requested page, in language 'lang', is in the cache
    If not, use the backup cache.
    If the cache should not be used, return None
    """
    # Compute the language
    if not lang:
        lang = "sv" if "sv" in request.url_rule.rule else "en"
    if not usecache or current_app.config["TEST"]:
        return None, lang
    pagename = helpers.cache_name(page, lang=lang)
    try:
        with g.mc_pool.reserve() as client:
            # Look for the page, return if found
            art = client.get(pagename)
            if art is not None:
                return art, lang
            # Ff not, look for the backup of the page and return
            art = client.get(pagename + "_backup")
            if art is not None:
                return art, lang
    except Exception:
        # TODO what to do??
        pass
    # If nothing is found, return None
    return None, lang


def copytobackup(fields, lang):
    """Make backups of  all requested fields to their corresponding backup field."""
    for field in fields:
        with g.mc_pool.reserve() as client:
            art = client.get(field + lang)
            client.set(
                helpers.cache_name(field, lang) + "_backup",
                art,
                time=current_app.config["CACHE_TIME"],
            )


def searchresult(
    result,
    name="",
    searchfield="",
    imagefolder="",
    query="",
    searchtype="equals",
    title="",
    authorinfo=False,
    lang="",
    show_lang_switch=True,
    _cache=True,
):
    """Compute the search result."""
    helpers.set_language_switch_link(f"{name}_index", result)
    try:
        pagename = f"{name}_{urllib.parse.quote(result)}"
        art = helpers.check_cache(pagename, lang)
        if art is not None:
            return art
        show = "name,url,undertitel,lifespan,undertitel_eng"
        if query:
            hits = helpers.karp_query("minientry", {"q": query, "show": show})
        else:
            hits = helpers.karp_query(
                "minientry",
                {
                    "q": f"extended||and|{searchfield}.search|{searchtype}|{result}",
                    "show": show,
                },
            )
        title = title or result

        no_hits = hits["hits"]["total"]
        if no_hits > 0:
            picture = None
            if os.path.exists(  # noqa: PTH110
                f"{current_app.config.root_path}/static/images/{imagefolder}/{result}.jpg"
            ):
                picture = f"/static/images/{imagefolder}/{result}.jpg"
            page = render_template(
                "list.html",
                picture=picture,
                alphabetic=True,
                title=title,
                headline=title,
                hits=hits["hits"],
                authorinfo=authorinfo,
                show_lang_switch=show_lang_switch,
            )
            if no_hits >= current_app.config["CACHE_HIT_LIMIT"]:
                with contextlib.suppress(Exception), g.mc_pool.reserve() as client:
                    client.set(
                        helpers.cache_name(pagename, lang),
                        page,
                        time=current_app.config["CACHE_TIME"],
                    )
            return page

        return render_template("page.html", content=gettext("Contents could not be found!"))

    except Exception as e:
        return render_template(
            "page.html",
            content=f'{e}\n{current_app.config["KARP_BACKEND"]}: extended||and|{searchfield}.search|{searchtype}|{result}',  # noqa: E501
        )


def compute_organisation(lang="", infotext="", cache=True, url=""):
    """Compute organisation view."""
    helpers.set_language_switch_link("organisation_index", lang=lang)
    art, lang = getcache("organisation", lang, cache)
    if art is not None:
        return art

    infotext = helpers.get_infotext("organisation", request.url_rule.rule)
    if lang == "en":
        data = helpers.karp_query(
            "minientry",
            {
                "q": "extended||and|anything|regexp|.*",
                "show": "organisationsnamn,organisationstyp_eng",
            },
        )
        typefield = "type_eng"
    else:
        data = helpers.karp_query(
            "minientry",
            {
                "q": "extended||and|anything|regexp|.*",
                "show": "organisationsnamn,organisationstyp",
            },
        )
        typefield = "type"
    nested_obj = {}
    for hit in data["hits"]["hits"]:
        for org in hit["_source"].get("organisation", []):
            orgtype = helpers.unescape(org.get(typefield, "-"))
            if orgtype not in nested_obj:
                nested_obj[orgtype] = defaultdict(set)
            nested_obj[orgtype][org.get("name", "-")].add(hit["_id"])
    art = render_template(
        "nestedbucketresults.html",
        results=nested_obj,
        title=gettext("Organisations"),
        infotext=infotext,
        name="organisation",
        page_url=url,
    )
    try:
        with g.mc_pool.reserve() as client:
            client.set(
                helpers.cache_name("organisation", lang),
                art,
                time=current_app.config["CACHE_TIME"],
            )
    except Exception:
        # TODO what to do?
        pass
    return art


def compute_activity(lang="", cache=True, url=""):
    """Compute activity view."""
    helpers.set_language_switch_link("activity_index", lang=lang)
    art, lang = getcache("activity", lang, cache)

    if art is not None:
        return art

    infotext = helpers.get_infotext("activity", request.url_rule.rule)

    # Fix list with references to be inserted in results
    reference_list = static_info.activities_reference_list
    [ref.append("reference") for ref in reference_list]

    art = bucketcall(
        queryfield="verksamhetstext",
        name="activity",
        title=gettext("Activities"),
        infotext=infotext,
        alphabetical=True,
        description=helpers.get_shorttext(infotext),
        insert_entries=reference_list,
        page_url=url,
    )
    try:
        with g.mc_pool.reserve() as client:
            client.set(
                helpers.cache_name("activity", lang),
                art,
                time=current_app.config["CACHE_TIME"],
            )
    except Exception:
        # TODO what to do?
        pass
    return art


def compute_article(lang="", url="", *, cache=True, with_map=False):
    """Compute article view."""
    helpers.set_language_switch_link("article_index", lang=lang)
    art, lang = getcache("article", lang, cache)
    if art is not None:
        return art

    show = "name,url,undertitel,lifespan,undertitel_eng,platspinlat.bucket,platspinlon.bucket"
    infotext = helpers.get_infotext("article", request.url_rule.rule)
    if lang == "sv":
        data = helpers.karp_query(
            "minientry",
            {
                "q": "extended||and|namn|exists",
                "show": show,
                "sort": "sorteringsnamn.sort,sorteringsnamn.init,tilltalsnamn.sort",
            },
            mode=current_app.config["SKBL_LINKS"],
        )
    else:
        data = helpers.karp_query(
            "minientry",
            {
                "q": "extended||and|namn|exists",
                "show": show,
                "sort": "sorteringsnamn.eng_sort,sorteringsnamn.eng_init,sorteringsnamn.sort,tilltalsnamn.sort",  # noqa: E501
            },
            mode=current_app.config["SKBL_LINKS"],
        )

    if with_map:
        art = render_template(
            "map.html",
            hits=data["hits"],
            headline=gettext("Map"),
            infotext=infotext,
            title="Map",
            page_url=url,
        )
    else:
        art = render_template(
            "list.html",
            hits=data["hits"],
            headline=gettext("Women A-Z"),
            alphabetic=True,
            split_letters=True,
            infotext=infotext,
            title="Articles",
            page_url=url,
        )
    try:
        with g.mc_pool.reserve() as client:
            client.set(
                helpers.cache_name("article", lang),
                art,
                time=current_app.config["CACHE_TIME"],
            )
    except Exception:
        # TODO what to do?
        pass
    return art


def compute_map(lang="", cache=True, url=""):
    """Compute article view."""
    helpers.set_language_switch_link("map", lang=lang)
    art, lang = getcache("map", lang, cache)
    if art is not None:
        return art

    show = "name,url,undertitel,lifespan,undertitel_eng,platspinlat.bucket,platspinlon.bucket"
    infotext = helpers.get_infotext("map", request.url_rule.rule)
    if lang == "sv":
        data = helpers.karp_query(
            "minientry",
            {
                "q": "extended||and|namn|exists",
                "show": show,
                "sort": "sorteringsnamn.sort,sorteringsnamn.init,tilltalsnamn.sort",
            },
            mode=current_app.config["KARP_MODE"],
        )
    else:
        data = helpers.karp_query(
            "minientry",
            {
                "q": "extended||and|namn|exists",
                "show": show,
                "sort": "sorteringsnamn.eng_sort,sorteringsnamn.eng_init,sorteringsnamn.sort,tilltalsnamn.sort",  # noqa: E501
            },
            mode=current_app.config["KARP_MODE"],
        )

    art = render_template(
        "map.html",
        hits=data["hits"],
        headline=gettext("Map"),
        infotext=infotext,
        title="Map",
        page_url=url,
    )
    try:
        with g.mc_pool.reserve() as client:
            client.set(
                helpers.cache_name("map", lang),
                art,
                time=current_app.config["CACHE_TIME"],
            )
    except Exception:
        # TODO what to do?
        pass
    return art


def compute_place(lang="", cache=True, url=""):
    """Compute place view."""
    helpers.set_language_switch_link("place_index", lang=lang)
    art, lang = getcache("place", lang, cache)
    if art is not None:
        return art
    infotext = helpers.get_infotext("place", request.url_rule.rule)

    def parse(kw):
        place = kw.get("key")
        # May be used to parse names with or without coordinates:
        # "Lysekil" or "Lysekil|58.275573|11.435558"
        if "|" in place:
            name, lat, lon = place.split("|")
        else:
            name = place.strip()
            lat, lon = 0, 0
        placename = name or f"{lat}, {lon}"
        return {"name": placename, "lat": lat, "lon": lon, "count": kw.get("doc_count")}

    def has_name(kw):
        name = kw.get("key").split("|")[0]
        return name if name and "(osäker uppgift)" not in name else None

    # To use the coordinates, use "getplaces" instead of "getplacenames"
    data = helpers.karp_query("getplacenames/" + current_app.config["KARP_MODE"], {})
    stat_table = [parse(kw) for kw in data["places"] if has_name(kw)]
    art = render_template(
        "places.html",
        places=stat_table,
        title=gettext("Placenames"),
        infotext=infotext,
        description=helpers.get_shorttext(infotext),
        page_url=url,
    )
    try:
        with g.mc_pool.reserve() as client:
            client.set(
                helpers.cache_name("place", lang),
                art,
                time=current_app.config["CACHE_TIME"],
            )
    except Exception:
        # TODO what to do?
        pass
    return art


def compute_artikelforfattare(infotext="", description="", lang="", cache=True, url=""):
    """Compute authors view."""
    helpers.set_language_switch_link("articleauthor_index", lang=lang)
    art, lang = getcache("author", lang, cache)
    if art is not None:
        return art
    q_data = {"buckets": "artikel_forfattare_fornamn.bucket,artikel_forfattare_efternamn.bucket"}
    data = helpers.karp_query("statlist", q_data)
    # strip kw0 to get correct sorting
    stat_table = [[kw[0].strip()] + kw[1:] for kw in data["stat_table"] if kw[0]]
    stat_table = [[f"{kw[1]},", kw[0], kw[2]] for kw in stat_table]

    # Remove duplicates and some wrong ones (because of backend limitation)
    # For articles that have more than one author the non existing name combinations are
    # listed here.
    stoplist = {
        "Grevesmühl,Kajsa": True,
        "Ohrlander,Anders": True,
        "Petré,Stefan": True,
        "Hammenbeck,Margareta": True,
        "Myrberg Burström,Mats": True,
        "Burström,Nanouschka": True,
        "Ljung,Yvonne": True,
        "Lindholm,Barbro": True,
        "Formark,Fredrik": True,
        "Mandelin,Bodil": True,
        "Sedin,Els-Marie": True,
        "Rådström,Inger": True,
        "Mannerheim,Madeleine": True,
        "Kleberg,Ylva": True,
        "Kärnekull,Anneka ": True,
        "Kärnekull,Ingrid": True,
        "Kärnekull,Paul": True,
        "Kärnekull,Per": True,
        "Lewis,Ingrid": True,
        "Lewis,Kerstin": True,
        "Lewis,Paul": True,
        "Lewis,Per": True,
        "Rydberg,Anette": True,
        "Rydberg,Anneka": True,
        "Rydberg,Kerstin": True,
        "Rydberg,Paul": True,
        "Rydberg,Per": True,
        "Anderson,Anneka": True,
        "Anderson,Ingrid": True,
        "Anderson,Kerstin": True,
    }
    added = {}
    new_stat_table = []
    for item in stat_table:
        fullname = item[0] + item[1]
        if fullname not in added and fullname not in stoplist:
            new_stat_table.append(item)
            added[fullname] = True
    art = render_template(
        "bucketresults.html",
        results=new_stat_table,
        alphabetical=True,
        title=gettext("Article authors"),
        name="articleauthor",
        infotext=infotext,
        description=description,
        sortnames=True,
        page_url=url,
    )
    try:
        with g.mc_pool.reserve() as client:
            client.set(
                helpers.cache_name("author", lang),
                art,
                time=current_app.config["CACHE_TIME"],
            )
    except Exception:
        # TODO what to do?
        pass
    return art


def bucketcall(
    queryfield="",
    name="",
    title="",
    sortby="",
    lastnamefirst=False,
    infotext="",
    description="",
    query="",
    alphabetical=False,
    insert_entries=None,
    page_url="",
):
    """Bucket call helper."""
    q_data = {"buckets": f"{queryfield}.bucket"}
    if query:
        q_data["q"] = query
    data = helpers.karp_query("statlist", q_data)
    # Strip kw0 to get correct sorting
    stat_table = [[kw[0].strip()] + kw[1:] for kw in data["stat_table"] if kw[0]]

    # Insert entries that function as references
    if insert_entries:
        stat_table.extend(insert_entries)
    if sortby:
        stat_table.sort(key=sortby)
    else:
        stat_table.sort(key=operator.itemgetter(0))
    if lastnamefirst:
        stat_table = [[f"{kw[1]},", kw[0], kw[2]] for kw in stat_table]
    # if showfield:
    #     stat_table = [[showfield(kw), kw[2]] for kw in stat_table]
    return render_template(
        "bucketresults.html",
        results=stat_table,
        alphabetical=alphabetical,
        title=gettext(title),
        name=name,
        infotext=infotext,
        description=description,
        page_url=page_url,
    )


def compute_emptycache(fields):
    """Empty the cache (but leave the backupfields).

    Only users with write permission may do this
    May raise error, eg if the authorization does not work
    """
    emptied = False
    auth = request.authorization
    user, pw = auth.username, auth.password
    postdata = {
        "username": user,
        "password": pw,
        "checksum": md5(
            user.encode() + pw.encode() + current_app.config["SECRET_KEY"].encode()
        ).hexdigest(),
    }
    server = current_app.config["WSAUTH_URL"]
    contents = urlopen(server, urllib.parse.urlencode(postdata).encode()).read()
    auth_response = json.loads(contents)
    lexitems = auth_response.get("permitted_resources", {})
    rights = lexitems.get("lexica", {}).get(current_app.config["KARP_LEXICON"], {})
    if rights.get("write"):
        with g.mc_pool.reserve() as client:
            for field in fields:
                client.delete(f"{field}sv")
                client.delete(f"{field}en")
        emptied = True
    return emptied


def compute_contact_form():
    """Compute view for contact form ."""
    helpers.set_language_switch_link("contact")

    email = request.form["email"].strip()
    required_fields = ["name", "email"]

    if request.form["mode_switch"] == "suggest_new":
        mode = "suggestion"
        required_fields.extend(
            ["subject_name", "subject_lifetime", "subject_activity", "motivation"]
        )
    elif request.form["mode_switch"] == "correction":
        mode = "correction"
        required_fields.append("message")
    else:
        mode = "other"
        required_fields.append("message")

    error_msgs = []
    errors = []
    for field in required_fields:
        if not request.form[field]:
            error_msgs.append(gettext("Please enter all the fields!"))
            errors.append(field)

    if email and not helpers.is_email_address_valid(email):
        error_msgs.append(gettext("Please enter a valid email address!"))

    if error_msgs := list(set(error_msgs)):
        return render_template(
            "contact.html",
            title=gettext("Contact"),
            headline=gettext("Contact SKBL"),
            errors=error_msgs,
            name_error="name" in errors,
            email_error="email" in errors,
            message_error="message" in errors,
            subject_name_error="subject_name" in errors,
            subject_lifetime_error="subject_lifetime" in errors,
            subject_activity_error="subject_activity" in errors,
            motivation_error="motivation" in errors,
            form_data=request.form,
            mode=mode,
        )

    return make_email(request.form, mode)


def make_email(form_data, mode="other"):
    """Compose and send email from contact form."""
    name = form_data["name"].strip()
    email = form_data["email"].strip()
    recipient = current_app.config["EMAIL_RECIPIENT"]
    complete_sender = f"{name} <{email}>"

    # If email address contains non-ascii chars it won't be accepted by the server as sender.
    # Non-ascii chars in the name will produce weirdness in the from-field.
    if helpers.is_ascii(email) and helpers.is_ascii(name):
        sender = complete_sender
    elif helpers.is_ascii(email):
        sender = email
    else:
        sender = recipient

    if mode == "suggestion":
        text = [f"{complete_sender} har skickat in ett förslag för en ny SKBL-ingång.\n\n"]
        text.extend(
            (
                f"Förslag på kvinna: {form_data['subject_name']}\n",
                "Kvinnas levnadstid: {}\n".format(form_data["subject_lifetime"]),
                "Kvinnas verksamhet: {}\n".format(form_data["subject_activity"]),
                "Motivering: {}\n".format(form_data["motivation"]),
            )
        )
        text = "".join(text)
        subject = "Förslag för ny ingång i skbl.se"
    elif mode == "correction":
        text = "{} har skickat följande meddelande:\n\n{}".format(
            complete_sender,
            form_data["message"],
        )
        subject = "Förslag till rättelse (skbl.se)"
    else:
        text = "{} har skickat följande meddelande:\n\n{}".format(
            complete_sender,
            form_data["message"],
        )
        subject = "Förfrågan från skbl.se"

    html = text.replace("\n", "<br>")
    part1 = MIMEText(text, "plain", "utf-8")
    part2 = MIMEText(html, "html", "utf-8")

    msg = MIMEMultipart("alternative")
    msg.attach(part1)
    msg.attach(part2)

    msg["Subject"] = subject
    msg["To"] = recipient
    msg["From"] = sender

    server = smtplib.SMTP(current_app.config["EMAIL_SERVER"])
    server.sendmail(sender, recipient, msg.as_string())
    server.quit()

    # Render user feedback
    return render_template(
        "form_submitted.html",
        title=gettext("Thank you for your feedback") + "!",
        headline=gettext("Thank you for your feedback") + ", " + name + "!",
        text=gettext("We will get back to you as soon as we can."),
    )
