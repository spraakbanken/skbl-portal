# SKBL.SE

## Run development

`docker-compose up`

Visit http://localhost:8080

## Re-build container
`docker-compose down`
`docker-compose build`
`docker-compose up`

## Update translations

### Extract translations
pybabel extract -F babel.cfg -o app/translations/messages.pot .

### Update translations
pybabel update -i app/translations/messages.pot -d app/translations
(add translations by modifying messages.po)

### Compile translations
pybabel compile -d app/translations

## TODO
Implement list calls for:

Verksamhet:
https://ws.spraakbanken.gu.se/ws/karp/v3/statlist?mode=skbl&resource=skbl&buckets=verksamhetstext.bucket
https://ws.spraakbanken.gu.se/ws/karp/v3/statlist?mode=skbl&resource=skbl&buckets=verksamhetstyp.bucket

Organistion:
https://ws.spraakbanken.gu.se/ws/karp/v3/statlist?mode=skbl&resource=skbl&buckets=organisationsnamn.bucket
https://ws.spraakbanken.gu.se/ws/karp/v3/statlist?mode=skbl&resource=skbl&buckets=organisationstext.bucket
https://ws.spraakbanken.gu.se/ws/karp/v3/statlist?mode=skbl&resource=skbl&buckets=organisationstyp.bucket

Platser:
https://ws.spraakbanken.gu.se/ws/karp/v3/statlist?mode=skbl&resource=skbl&buckets=plats.bucket

Nyckelord:
https://ws.spraakbanken.gu.se/ws/karp/v3/statlist?mode=skbl&resource=skbl&buckets=nyckelord.bucket

Artikelförfattare (obs, ful):
https://ws.spraakbanken.gu.se/ws/karp/v3/statlist?mode=skbl&resource=skbl&buckets=artikel_forfattare_fornamn.bucket,artikel_forfattare_efternamn.bucket
