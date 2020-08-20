Overview
========

Shorty is a URL Shortening and custom redirect link provider.

With traditional URL shortening, it will generate a link based on the database
ID of the record (base36 encodded).

In addition to traditional shortening you may also create a custom keyword name.
These are isolated into namespaces (/global /~user, and any you add).

Features
========

* Create a shortend URL from any URL entered
* Reporting (Total hits, last used, created)
* Link time tracking (tracks create date and last time it was hit)
* External Authentication with LDAP
* Multi-user
* Namespaces
    * Namespaces for keywords (global and user by default, custom ones may be added)
    * Permissions for namespaces
* Database connection through sqlAlchemy via pugsql (Tested on MySQL and SQLite)

Methodology
===========

When an entry is added, it is added to the DB and given a unique "key".  This
key is base36 encoded and always compared as lowercase.  This way if you are
communicating the URL, it can be entered in any form and it will still work.
This is why we are using base36 (a-z+0-9)

Requirements
============

Ideally you would have a webserver running wgsi and point it at the wsgi.py file.  I have tested
this to work with uwsgi and nginx.

Installing
==========

I am working on getting this setup correctly through PyPI.  In the mean time it is a bit of a mess.
    1.  Clone the repo
    2.  Edit the conf/conf-dist.yaml with your values and save to conf.yaml
    3.  cd to cloned_path/shorty
    4.  run shorty.py
    5.  hit localhost:5000

    That should make a connection to the DB and create the tables and you should be on your way

Eventually I want to get the setuptools configured properly to do a normal install via whatever method you want

Inspiration
===========

When trying to figure out the best way to accomplish a URL shortener, I found
this https://github.com/narenaryan/Pyster which I used as the base.  I modified
it HEAVILY, but to give credit where it is due, that is what I used as the base.
