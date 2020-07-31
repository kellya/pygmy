#!/usr/bin/env python
from flask import Flask, request, render_template, redirect, g, Response
from flask_simpleldap import LDAP
from urllib.parse import urlparse
from sqlite3 import OperationalError
import sqlite3
import base36
import datetime
import calendar
import os
import time


def uri_validator(x):
    """ Determines if a given URL is valid and returns True/False"""
    # This code was obtained from a stackoverflow answer at:
    # https://stackoverflow.com/questions/7160737/python-how-to-validate-a-url-in-python-malformed-or-not
    try:
        result = urlparse(x)
        return all([result.scheme, result.netloc, result.path])
    except:
        return False


def table_check():
    """Verify the tables exist in the db"""
    create_redirect_table = """
        CREATE TABLE "redirect"(
        "id" INTEGER PRIMARY KEY AUTOINCREMENT,
        "url" TEXT NOT NULL,
        "owner" TEXT DEFAULT 0,
        "createTime" INTEGER,
        "lastUsed" INTEGER,
        "hit" INTEGER DEFAULT 0,
        "keyword" TEXT UNIQUE
        );
        """
    create_permission_table = """
        CREATE TABLE "permission" (
        "id"	TEXT NOT NULL UNIQUE,
        "admin"	INTEGER,
        "edit"	INTEGER,
        "keyword"	INTEGER,
        PRIMARY KEY("id")
    );
    """
    with sqlite3.connect('urls.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(create_redirect_table)
            cursor.execute(create_permission_table)
        except OperationalError:
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
app.config['LDAP_USER_OBJECT_FILTER'] = os.environ['LDAP_USER_OBJECT_FILTER']
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
        with sqlite3.connect('urls.db') as conn:
            cursor = conn.cursor()
            result_cursor = cursor.execute(f"SELECT id FROM redirect WHERE keyword = '{recordid}'")
            recordid = result_cursor.fetchone()[0]

    with sqlite3.connect('urls.db') as conn:
        cursor = conn.cursor()
        update_sql = f'UPDATE redirect SET hit = hit + 1 WHERE id = {recordid}'
        result_cursor = cursor.execute(update_sql)

        update_sql = f'UPDATE redirect SET lastUsed = {timestamp} WHERE id = {recordid}'
        result_cursor = cursor.execute(update_sql)


def setDefaultPermissions(username):
    """
    Create a default permission set for a user if they are not already in the db
    :param username:UID from LDAP
    :return:  None
    """
    insertQuery = f"INSERT INTO permission (id, edit) values ('{username}', 1)"
    with sqlite3.connect('urls.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(insertQuery)
        except Exception as e:
            print(e)


def getPermissions(username):
    """
    Gets user permissions from db, or creates a default value if user isn't already in the DB
    :param username: uid from LDAP
    :return: A dictionary containing permissions as returned from the DB
    """
    returnQuery = f"SELECT * FROM permission WHERE id = '{username}'"
    with sqlite3.connect('urls.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            result_cursor = cursor.execute(returnQuery)
            results = [dict(row) for row in result_cursor.fetchall()]
            return results[0]
        except IndexError:
            setDefaultPermissions(username)
            getPermissions(username)


@app.route('/', methods=['GET', 'POST'])
@ldap.basic_auth_required
def home():
    """
    Display the home/entry page for the shortener
    :return:  jinja template for /home.html
    """
    errors = []
    permissions = getPermissions(g.ldap_username)
    if request.method == 'POST':
        original_url = request.form.get('url')
        keyword = request.form.get('keyword')
        if not original_url.startswith('http'):
            original_url = 'http://' + original_url
        if not uri_validator(original_url):
            errors.append(f'URL {original_url} is not in the proper format')
        try:
            if not keyword[0].isalnum():
                errors.append(f'Keyword must start with an alphanumeric character')
        except IndexError:
            # If we weren't given a keyword, just pass
            pass
        if len(errors) == 0:
            timestamp = calendar.timegm(datetime.datetime.now().timetuple())
            with sqlite3.connect('urls.db') as conn:
                cursor = conn.cursor()
                if len(keyword) > 0:
                    insert_row = f"""
                        INSERT INTO redirect (url, owner, createTime, keyword)
                        VALUES ('{original_url}', '{g.ldap_username}', '{timestamp}', '{keyword}')
                    """
                else:
                    insert_row = f"""
                        INSERT INTO redirect (url, owner, createTime)
                            VALUES ('{original_url}', '{g.ldap_username}', '{timestamp}')
                        """

                try:
                    result_cursor = cursor.execute(insert_row)
                    encoded_string = "+" + base36.dumps(result_cursor.lastrowid)
                except sqlite3.IntegrityError:
                    errors.append(f'Keyword {keyword} is already used')
                    encoded_string = ""
                # Prepend the string with a + so we can differentiate between shortURL and custom Redirects
                url_base = f'{request.scheme}://{request.host}' or None
            return render_template('home.html',
                                   url_base=url_base,
                                   short_url=encoded_string,
                                   keyword=keyword,
                                   errors=errors,
                                   permissions=permissions,
                                   )
    return render_template('home.html', errors=errors, permissions=permissions)


@app.route('/help')
def showhelp():
    """
    Displays the help page
    :return: jinja template for help.html
    """
    # FIXME: This permissions setting shouldn't be forced here, but permissions is called from base, so it has to exist
    permissions = {'admin': None, 'edit': None, 'keyword': None}
    return render_template('help.html', permissions=permissions)


@app.route('/logout')
def logout():
    """
   Haphazardly handles a logout action for a basic authentication, which isn't really a thing for basic-auth
    :return:
    """
    return Response('User Logout', 401, {'WWW-Authenticate': 'Basic realm="Franklin SSO"'})


@app.route('/mylinks')
@ldap.basic_auth_required
def mylinks():
    """
    Displays all the links created by the logged-in user
    :return: jinja template render for links.html
    """
    permissions = getPermissions(g.ldap_username)
    with sqlite3.connect('urls.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        result_cursor = cursor.execute(f"SELECT * FROM redirect WHERE owner = '{g.ldap_username}'")
        results = [dict(row) for row in result_cursor.fetchall()]
    return render_template('links.html', results=results, permissions=permissions)


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
        redirect_url = request.host
        with sqlite3.connect('urls.db') as conn:
            cursor = conn.cursor()
            select_row = f"""SELECT url FROM redirect WHERE id={decoded_string}"""
            result_cursor = cursor.execute(select_row)
            try:
                redirect_url = result_cursor.fetchone()[0]
                hit_increase(decoded_string)
            except Exception as e:
                print(e)
    else:
        with sqlite3.connect('urls.db') as conn:
            cursor = conn.cursor()
            select_row = f"""
                SELECT url FROM redirect WHERE keyword = '{short_url}';
            """
            result_cursor = cursor.execute(select_row)
            try:
                redirect_url = result_cursor.fetchone()[0]
                hit_increase(short_url)
            except Exception as e:
                print(e)
    try:
        return redirect(redirect_url)
    except UnboundLocalError:
        return render_template('error.html', url=short_url)


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
    # This code checks whether database table is created or not
    table_check()
    app.run(host="0.0.0.0", debug=True)
