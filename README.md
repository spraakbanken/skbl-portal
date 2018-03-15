# SKBL.SE

## Run development

`docker-compose up`

Visit http://localhost:8080

## Re-build container
    docker-compose down
    docker-compose build
    docker-compose up

## Extract, update and compile translations
    docker-compose exec web pybabel extract -F babel.cfg -o app/translations/messages.pot .
    docker-compose exec web pybabel update -i app/translations/messages.pot -d app/translations

Add translations by modifying messages.po
If you don't have permission to modify messages.po run the following command:

    docker-compose exec web chmod -R 777 app/translations/sv/LC_MESSAGES/messages.po

Finally compile:

    docker-compose exec web pybabel compile -d app/translations
