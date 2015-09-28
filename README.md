Flask API Boilerplate
==================

Boilerplate flask configuration to create REST based web service projects.

It supports OAuth 2.0 authentification (only through the 'Password' authentication scheme for now). It also supports [conditional requests] (http://fideloper.com/api-etag-conditional-get), and provides [concurrency control management](http://fideloper.com/etags-and-optimistic-concurrency-control)  through the use of [entity tags](http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html).


Dependencies
------------

* [Flask](http://flask.pocoo.org/)
* [Restless](http://restless.readthedocs.org/en/latest/)
* Flask Script
* Flask Migrate
* [SQLAlchemy](http://www.sqlalchemy.org/)
* Flask SQLAlchemy
* [Flask OAuthLib](https://github.com/lepture/flask-oauthlib)

For all requirements see the file [requirements.txt](requirements.txt)


Usage
-----

* Clone the repo

```$ git clone https://github.com/niclabs/flask-rest-boilerplate.git```

* Initialize the virtual environment (python 2.7+ and 3.4+ supported)

```
$ virtualenv venv --distribute --no-site-packages
$ source venv/bin/activate
```

* Download required packages

```
(venv)$ pip install -r requirements.txt
```

* Run the server
```
(venv)$ python manage.py runserver
```

The server should now be running on [localhost:5000](http://localhost:5000)
