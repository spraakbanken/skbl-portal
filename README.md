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
docker-compose exec web pybabel extract -F babel.cfg -o app/translations/messages.pot .

### Update translations
docker-compose exec web pybabel update -i app/translations/messages.pot -d app/translations

Add translations by modifying messages.po
If you don't have permission to modify messages.po run the following command:
docker-compose exec web chmod -R 777 .

### Compile translations
docker-compose exec web pybabel compile -d app/translations

### Installing memcached & co on k2
Download and install memcached, libmemcached and libevent.
For example:
`./configure --prefix=/var/www/sites/dev.skbl.se/data/libevent`
`make`
`make test`
`make install`

For memcached, run the config as below
`./configure --prefix=/var/www/sites/dev.skbl.se/data/memcached --with-libevent=/var/www/sites/dev.skbl.se/data/libevent`

To get pylibmc to work with the locally installed mc packages, run:
pip install --global-option=build_ext --global-option="-I/home/fkskbl/dev.skbl.se/data/libmemcached/include/" --global-option="-L/home/fkskbl/dev.skbl.se/data/libmemcached/lib" --global-option="-R/home/fkskbl/dev.skbl.se/data/libmemcached/lib" pylibmc


