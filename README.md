# SKBL.SE

## Run development

`docker-compose up`

Visit http://localhost:8080

## Update translations

### Extract translations
pybabel extract -F babel.cfg -o app/translations/messages.pot .

### Update translations
pybabel update -i app/translations/messages.pot -d app/translations

### Compile translations
pybabel compile -d app/translations

## TODO
Implement list calls for:

Verksamhet:
https://ws.spraakbanken.gu.se/ws/swo/statlist?buckets=verksamhetstext.bucket
https://ws.spraakbanken.gu.se/ws/swo/statlist?buckets=verksamhetstyp.bucket

Organistion:
https://ws.spraakbanken.gu.se/ws/swo/statlist?buckets=organisationsnamn.bucket
https://ws.spraakbanken.gu.se/ws/swo/statlist?buckets=organisationstext.bucket
https://ws.spraakbanken.gu.se/ws/swo/statlist?buckets=organisationstyp.bucket

Platser:
https://ws.spraakbanken.gu.se/ws/swo/statlist?bukets=plats.bucket

Nyckelord:
https://ws.spraakbanken.gu.se/ws/swo/statlist?buckets=nyckelord.bucket

Artikelförfattare (obs, ful):
https://ws.spraakbanken.gu.se/ws/swo/statlist?bukets=artikel_forfattare_fornamn.bucket,artikel_forfattare_efternamn.bucket