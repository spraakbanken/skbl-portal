# SKBL.SE

## Run development
* Copy `app/config.default.cfg` to `app/config.cfg`
* Set KARP_AUTH_HASH to secret value (retrieved from another developer)
* Run `docker-compose up`
* Visit http://localhost:8080

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


## Installing memcached & co on server
Download and install libevent, memcached, libmemcached.
For example:

    ./configure --prefix=/var/www/sites/dev.skbl.se/data/libevent
    make
    make test
    make install

For memcached, run the config as below

```
./configure --prefix=/var/www/sites/dev.skbl.se/data/memcached --with-libevent=/var/www/sites/dev.skbl.se/data/libevent
```

To get pylibmc to work with the locally installed memcached packages, run:

`LIBMEMCACHED=~/memcached/ pip install pylibmc`

Where `~/memcached/` is the path to your locally installed memcached.

If this does not work, try:
```
pip install --global-option=build_ext --global-option="-I/home/fkskbl/dev.skbl.se/data/libmemcached/include/" --global-option="-L/home/fkskbl/dev.skbl.se/data/libmemcached/lib" --global-option="-R/home/fkskbl/dev.skbl.se/data/libmemcached/lib" pylibmc
```

### Running memcached

Unless you're using Docker, you need to start memcached on the server. If you're using [supervisor](http://supervisord.org/running.html),
add the following lines to your config (`/etc/supervisor.d/fkskbl.conf`):

```
[program:memcached]
command=/path/to/installedmemcached/memcached/bin/memcached
        -s /path/to/socketfile/memcached.sock
        -v
        -a 770
```

Then run

`supervisorctl -c /etc/supervisord.d/fkskbl.conf update`

and

`supervisorctl -c /etc/supervisord.d/fkskbl.conf status`

to see that the process has started successfully.
