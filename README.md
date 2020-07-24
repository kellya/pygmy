# Overview
This is a URL shortening service that works like any typical URL shortening
service, except that it also allows you to specify a keyword as a URL in
addition to the "random" short link

# Features

## Current
* Create a shortend URL from any URL entered
* Reporting (Hit count is updated, but actual report is planned)
* Link time tracking (tracks create date and last time it was hit)

## Planned
* Multi-user (partially implemented)
* External Authentication

# Methodology
When an entry is added, it is added to the DB and given a unique "key".  This
key is base36 encoded and always compared as lowercase.  This way if you are
communicating the URL, it can be entered in any form and it will still work.
This is why we are using base36 (a-z+0-9)

# Inspiration
When trying to figure out the best way to accomplish a URL shortener, I found
this https://github.com/narenaryan/Pyster which I used as the base.  I modified
it HEAVILY, but to give credit where it is due, that is what I used as the base.
