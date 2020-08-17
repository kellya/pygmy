#!/usr/bin/env python
from flask import Flask, request, render_template, redirect, g, Response, url_for
from flask_simpleldap import LDAP
from urllib.parse import urlparse
from sqlite3 import OperationalError
import sqlite3
import base36
import datetime
import calendar
import os
import time
import pugsql
from pbr.version import VersionInfo

__version__ = VersionInfo('shorty').release_string()

metainfo = {
    'version': __version__,
    'changelog': 'https://git.admin.franklin.edu/tins/shorty/raw/branch/master/ChangeLog'
}

queries = pugsql.module('sql/')
queries.connect('sqlite:///urls.db')


def uri_validator(uri):
    """ Determines if a given URL is valid and returns True/False"""
    # This code was obtained from a stackoverflow answer at:
    # https://stackoverflow.com/questions/7160737/python-how-to-validate-a-url-in-python-malformed-or-not
    try:
        result = urlparse(uri)
        return all([result.scheme, result.netloc, result.path])
    except:
        return False


def table_check():
    """Verify the tables exist in the db"""
    try:
        queries.create_owner_table()
        queries.create_namespace_table()
        queries.create_permission_table()
        queries.insert_default_permissions()
        queries.create_namespacepermission_table()
        queries.create_redirect_table()
        queries.create_apppermission_table()
    except Exception as e:
        pass


app = Flask(__name__)
ldap_vars = [
    'LDAP_HOST',
    'LDAP_BASE_DN',
    'LDAP_USERNAME',
    'LDAP_PASSWORD',
    'LDAP_REALM_NAME',
    'LDAP_USER_OBJECT_FILTER',
]
for var in ldap_vars:
    if var not in os.environ:
        raise EnvironmentError(f'{var} must be exported as an environment variable\n\t \'export {var}="value"\'')

app.config['LDAP_REALM_NAME'] = os.environ['LDAP_REALM_NAME']
app.config['LDAP_HOST'] = os.environ['LDAP_HOST']
app.config['LDAP_BASE_DN'] = os.environ['LDAP_BASE_DN']
app.config['LDAP_USERNAME'] = os.environ['LDAP_USERNAME']
app.config['LDAP_PASSWORD'] = os.environ['LDAP_PASSWORD']
app.config['LDAP_OPENLDAP'] = True
app.config['LDAP_USER_OBJECT_FILTER'] = '(&(objectclass=inetOrgPerson)(uid=%s))'
ldap = LDAP(app)


def hit_increase(recordid):
    """
    Updates the hit count and last used timestamp for recordid
    :param recordid: int or string specifying a unique record
    :return: None
    """
    timestamp = calendar.timegm(datetime.datetime.now().timetuple())
    if type(recordid) == str:
        # We need to get the ID for the shortname/keyword
        recordid = queries.get_record_by_keyword(keyword=recordid)['id']

    queries.update_redirect_hits(lastUsed=timestamp, recordid=recordid)


def get_userid(username):
    """
    Returns the numeric ID of the username given or False if no user matches
    :param username:
    :return: int
    """
    try:
        userid = queries.get_id_from_name(username=username)['id']
        return userid
    except Exception as e:
        return False


def set_default_permissions(username):
    print(username)
    """
    Create a default permission set for a user if they are not already in the db
    :param username:UID from LDAP
    :return:  None
    """
    userid = get_userid(username)
    queries.create_owner_entry(username=username)
    queries.create_owner_default_permissions(owner=userid)


def get_permissions(username):
    """
    Gets user permissions from db, or creates a default value if user isn't already in the DB
    :param username: uid from LDAP
    :return: A dictionary containing permissions as returned from the DB
    """
    userid = get_userid(username)
    permissions = []
    if not userid:
        # if we don't have a username from the db, it's a new user, so create it and call back
        set_default_permissions(username)
        get_permissions(username)
    for permission in queries.get_user_permissions(owner=userid):
        permissions.append(permission['name'])
    return permissions


@app.route('/', methods=['GET', 'POST'])
@ldap.basic_auth_required
def home():
    """
    Display the home/entry page for the shortener
    :return:  jinja template for /home.html
    """
    errors = []
    # Set the username once so we don't have to keep querying it
    username = g.ldap_username
    # Get the numeric ID of teh user (maybe make it so we
    userid = get_userid(username)
    print(userid)
    permissions = get_permissions(username)
    if request.method == 'POST':
        original_url = request.form.get('url')
        keyword = request.form.get('keyword')
        if not original_url.startswith('http'):
            original_url = 'http://' + original_url
        if not uri_validator(original_url):
            errors.append(f'URL {original_url} is not in the proper format')
        try:
            if len(keyword) > 0 and not keyword.isalnum():
                errors.append(f'Keyword must only contain alpha-numeric characters.')
        except IndexError:
            # If we weren't given a keyword, just pass
            pass
        namespace = 1  # REMOVE AFTER NAMESPACES ARE WORKING!!!
        if len(errors) == 0:
            timestamp = calendar.timegm(datetime.datetime.now().timetuple())
            if len(keyword) > 0:
                lastrowid = queries.insert_redirect_keyword(
                    url=original_url, owner=userid, createTime=timestamp, keyword=keyword, namespace=namespace
                )
            else:
                lastrowid = queries.insert_redirect(
                    url=original_url, owner=userid, createTime=timestamp, namespace=namespace
                )
            encoded_string = "+" + base36.dumps(lastrowid)
            #ATODO: Add dupe checking for keywords in namespace
            # Prepend the string with a + so we can differentiate between shortURL and custom Redirects
            url_base = f'{request.scheme}://{request.host}' or None
            return render_template('home.html',
                                   url_base=url_base,
                                   short_url=encoded_string,
                                   keyword=keyword,
                                   errors=errors,
                                   metainfo=metainfo,
                                   permissions=permissions,
                                   )
    return render_template('home.html', errors=errors, metainfo=metainfo, permissions=permissions)


@app.route('/_help')
def showhelp():
    """
    Displays the help page
    :return: jinja template for help.html
    """
    return render_template('help.html', metainfo=metainfo, permissions=permissions)


@app.route('/_logout')
def logout():
    """
   Haphazardly handles a logout action for a basic authentication, which isn't really a thing for basic-auth
    :return:
    """
    return Response('User Logout', 401, {'WWW-Authenticate': 'Basic realm="Franklin SSO"'})


@app.route('/_mylinks', methods=['GET'])
@ldap.basic_auth_required
def mylinks():
    username = g.ldap_username
    """
    Displays all the links created by the logged-in user
    :return: jinja template render for links.html
    """
    permissions = get_permissions(username)
    try:
        success = request.args['editsuccess']
    except Exception as e:
        success = False
    results = queries.get_shortcuts(owner=get_userid(username))
    return render_template('links.html', results=results, metainfo=metainfo, permissions=permissions,
                           editsuccess=success)


@app.route('/_edit', methods=['GET', 'POST'])
@ldap.basic_auth_required
def edit_link():
    username = g.ldap_username
    updateurl = request.form.get('url')
    permissions = get_permissions(username)
    userid = get_userid(username)

    if request.method == 'GET':
        recordid = base36.loads(request.args.get('id'))
        url = queries.get_record_by_id_with_owner(owner=userid, id=recordid)['url']
        try:
            return render_template('edit.html', url=url, metainfo=metainfo, permissions=permissions)
        except IndexError:
            return render_template('edit.html', url='', metainfo=metainfo, permissions=permissions,
                                   errors=['No permission to edit this ID'])
    elif request.method == 'POST':
        queries.update_redirect(updateurl=updateurl, owner=userid, id=request.args.get('id'))
        return redirect(url_for('mylinks', editsuccess=True))


@app.route('/_admin')
@ldap.basic_auth_required
def admin():
    permissions = get_permissions(g.ldap_username)
    return render_template('admin.html', permissions=permissions, metainfo=metainfo)


@app.route('/<namespace>/<keyword>')
def redirect_name_keyword(namespace, keyword):
    """
    Name-based keywords so that users can create their own redirects that don't overwrite globals
    :param namespace:
    :param keyword:
    :return:
    """
    return "This function not yet complete"

@app.route('/<short_url>')
def redirect_short_url(short_url):
    """
    Handles shortlink/keyword redirects by pulling the destination from the DB matching a base36 encoded version
    of the shortlink, or a /keyword link if the short_url does not start with a +
    :param short_url:
    :return:
    """
    short_url = short_url.lower()
    if short_url[0] == "+":
        decoded_string = base36.loads(short_url)
        try:
            redirect_url = queries.get_redirect_url(id=decoded_string)['url']
            hit_increase(decoded_string)
        except Exception as e:
            print(e)
    else:
        redirect_url = queries.get_redirect_keyword(keyword=short_url)['url']
        hit_increase(short_url)
    try:
        return redirect(redirect_url)
    except Exception as e:
        permissions = []
        return render_template('error.html', metainfo=metainfo, permissions=permissions, url=short_url)


@app.template_filter('humantime')
def format_datetime(value, timeformat='%Y-%m-%d'):
    """
    Filter to convert epoch (value) to the timeformat
    :param value:
    :param timeformat:
    :return:
    """
    if value is None:
        return ""
    return time.strftime(timeformat, time.localtime(value))


@app.template_filter('shortcode')
def format_shortcode(value):
    """
    Return the base36 encoded short URL version of a number
    :param value:
    :return:  shortcode of "+<base36 value of <value>>"
    """
    return "+" + base36.dumps(value)


@app.template_filter('elipses')
def format_elipses(value, length=100):
    """
    Return a string ending in ... for the string given
    Specify a negative number in the template to return everything
    """
    if len(value) < length:
        return value
    else:
        return value[:length] + "..."


if __name__ == '__main__':
    table_check()
    app.run(host="0.0.0.0", debug=True)
