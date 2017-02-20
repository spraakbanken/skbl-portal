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