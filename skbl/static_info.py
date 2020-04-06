# -*- coding=utf-8 -*-
"""Define some static strings used in the html."""

keywords_reference_list = [
    # [ non_existing_keyword, existing_keyword]
    [u"Advokater", u"Jurister"],
    [u"Ambassadörer", u"Diplomater"],
    [u"Flygare", u"Piloter"],
    [u"Idrott", u"Sport"],
    [u"Frågespalter", u"Rådgivningsspalter"],
    [u"Tonsättare", u"Kompositörer"]]

activities_reference_list = [
    # [ non_existing_keyword, existing_keyword]
    [u"Advokat", u"Jurist"],
    [u"Ambassadör", u"Diplomat"],
    [u"Flygare", u"Pilot"],
    [u"Hembiträde", u"Husligt arbete"],
    [u"Konsthantverk", u"Formgivare"],
    [u"Piga", u"Husligt arbete"],
    [u"Politiker", u"Kommun- och landstingspolitiker"],
    [u"Tonsättare", u"Kompositör"]]


infotexter = {
    "start": {
        "sv": u"""
<p>Läs om fler än 1 000 svenska kvinnor från medeltid till nutid.</p>
<p>Genom olika sökningar kan du se vad de arbetade med, vilken utbildning de fick, vilka organisationer de var med i,
hur de rörde sig i världen, vad de åstadkom och mycket mera.</p>
<p>Alla har de bidragit till samhällets utveckling.</p>
        """,
        "en": u"""
<p>Learn about more than 1000 Swedish women from the Middle Ages to the present day.</p>
<p>Use the search function to reveal what these women were about, how they were educated, which organisations they belonged to,
where they travelled, what they achieved, and much more.</p>
<p>All of them contributed in a significant way to the development of Swedish society.</p>
        """
    },

    "more-women": {
        "sv": u"""
Det finns många kvinnor som borde finnas med i Svenskt kvinnobiografiskt lexikon.
Ett urval har gjorts och här förtecknas de kvinnor vars biografier ännu inte finns med.
Den listan kan fyllas på med <a href='/sv/kontakt?suggest=true' class='visible_link'>ytterligare förslag</a>.
        """,
        "en": u"""
Many more women deserve entries in SKBL and a selection of these
can be found on this list. <a href='/en/contact?suggest=true' class='visible_link'>Further suggestions</a>
are welcome for inclusion on this list.
        """
    },

    "keyword": {
        "sv": u"""
Här finns en lista över de nyckelord som karaktäriserar materialet.
De utgörs av tid, yrken, religion och mycket mera.
Om du går in på något av nyckelorden kan du se vilka kvinnor som kan karaktäriseras med det.
        """,
        "en": u"""
This lists the keywords used to describe the material. They include dates, jobs, placenames,
religion, and much more. Selecting a keyword reveals all the women who fit into that descriptor.
        """
    },

    "articleauthor": {
        "sv": u"""
Här är de personerna som har bidragit med artiklar till Svenskt kvinnobiografiskt lexikon förtecknade.
        """,
        "en": u"""
This lists all those who have contributed an article to SKBL.
        """
    },

    "organisation": {
        "sv": u"""
Här kan du se vilka organisationer de biograferade kvinnorna varit medlemmar
och verksamma i. Det ger en inblick i de nätverks som var de olika kvinnornas och visar såväl
det gemensamma engagemanget som mångfalden i det. Om du klickar på organisationens namn visas
vilka kvinnor som var aktiva i den.
        """,
        "en": u"""
See which organisations the women were members of and active in. Get an insight into their networks
and shared activities as well as their extent. Selecting a particular organisation name will reveal
which women were involved in it.
        """
    },

    "activity": {
        "sv": u"""
Här kan du se inom vilka områden de biograferade kvinnorna varit verksamma och vilka yrken de hade.
        """,
        "en": u"""
See which activities the women engaged in and which professions they entered.
        """
    },

    "article": {
        "sv": u"""
Klicka på namnet för att läsa biografin om den kvinna du vill veta mer om.
        """,
        "en": u"""
Select the name of your chosen individual to access the accompanying biography.
        """
    },

    "place": {
        "sv": u"""
Här kan du se var de biograferade kvinnorna befunnit sig; var de fötts, verkat och dött.
Genom att klicka på en ort kan du se vilka som fötts, verkat och/eller avlidit där.
        """,
        "en": u"""
See where the women were active: their birth places, employment locations, and places of death.
Selecting a placename reveals which women were born, worked, or died there.

        """
    },

    "chronology": {
        "sv": u"""
Kronologin listar lexikonets kvinnor för en viss tidsperiod. Klicka och dra kontrollerna på tidsaxeln
för att avgränsa tidsperioden. Kronologin baseras på kvinnornas levnadsperiod, i den mån den har kunnat fastställas.
Den ger därmed en approximativ bild av deras verksamhetsperiod.

        """,
        "en": u"""
The chronology lists the women in the lexicon during a certain period. Click and drag the controls on the time axis
to delimit the period. The chronology is based on the women’s lifespan, to the degree it has been possible to establish it.
It therefore gives an approximate idea of their period of activity.
        """
    },

    "map": {
        "sv": u"""
Kartan visar geografisk anknytning för lexikonets kvinnor. Klicka på + och – för att förstora eller förminska kartan.
Varje cirkel på kartan anger antalet kvinnor med anknytning till respektive ort. Klicka på dessa cirklar tills de är
gröna för att se namnen på varje kvinna. Klicka på rutan längst upp till höger på kartan för att sortera den geografiska
anknytningen på orter för födelse, frånfälle, utbildning, verksamhet eller boende.
        """,
        "en": u"""
The map shows the geographical connections for the women in the lexicon. Click on + and – to make the map bigger or smaller.
Each circle on the map shows the number of women with connections to each respective place.
Click on these circles until they turn green to see the names of all the women.
Click on the box to the right on the map to sort the women’s geographical connections according to birthdate,
death, education, career or residence.
        """
    },

    "quiz": {
        "sv": u"""
Testa dina kvinnohistoriska kunskaper genom att besvara frågor i tre olika quiz. Klicka i den ruta du anser vara det rätta svaret.
När frågorna i ett quiz besvarats kan du klicka på knappen ”skicka”  och sedan ”visa resultat” för att se de rätta svaren.
        """,
        "en": u"""
Test your knowledge of women’s history by answering the questions in three different quizzes. Click on the box for what you think is the correct answer.
When all the questions in a quiz have been answered, you can click on the button “send” and then “show results” to see the correct answers.
        """
    },
}
