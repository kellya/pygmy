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
    create_table = """
        CREATE TABLE "WEB_URL"(
        "ID" INTEGER PRIMARY KEY AUTOINCREMENT,
        "URL" TEXT NOT NULL,
        "owner" TEXT DEFAULT 0,
        "createTime" INTEGER,
        "lastUsed" INTEGER,
        "hit" INTEGER DEFAULT 0,
        "keyword" TEXT UNIQUE
        );
        """
    with sqlite3.connect('urls.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(create_table)
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
            result_cursor = cursor.execute(f"SELECT ID FROM WEB_URL WHERE keyword = '{recordid}'")
            recordid = result_cursor.fetchone()[0]

    with sqlite3.connect('urls.db') as conn:
        cursor = conn.cursor()
        update_sql = f"""
                UPDATE WEB_URL SET hit = hit + 1 WHERE ID = {recordid}
            """
        result_cursor = cursor.execute(update_sql)

        update_sql = f"""
            UPDATE WEB_URL SET lastUsed = {timestamp}
                WHERE ID = {recordid}
"""
        result_cursor = cursor.execute(update_sql)


# Home page where user should enter
@app.route('/', methods=['GET', 'POST'])
@ldap.basic_auth_required
def home():
    errors = []
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
            # If we wren't given a keyword, just pass
            pass
        if len(errors) == 0:
            timestamp = calendar.timegm(datetime.datetime.now().timetuple())
            with sqlite3.connect('urls.db') as conn:
                cursor = conn.cursor()
                if len(keyword) > 0:
                    insert_row = """
                        INSERT INTO WEB_URL (URL, owner, createTime, keyword)
                            VALUES ('%s', '%s', '%s', '%s')
                        """ % (original_url, g.ldap_username, timestamp, keyword)
                else:
                    insert_row = """
                        INSERT INTO WEB_URL (URL, owner, createTime)
                            VALUES ('%s', '%s', '%s')
                        """ % (original_url, g.ldap_username, timestamp)

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
                                   )
    return render_template('home.html',errors=errors)


@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/logout')
def logout():
    return Response('User Logout', 401, {'WWW-Authenticate':'Basic realm="Franklin SSO"'})

@app.route('/mylinks')
@ldap.basic_auth_required
def mylinks():
    with sqlite3.connect('urls.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        result_cursor = cursor.execute(f"SELECT * FROM WEB_URL WHERE owner = '{g.ldap_username}'")
        results = [dict(row) for row in result_cursor.fetchall()]
    return render_template('links.html', results=results)


@app.route('/<short_url>')
def redirect_short_url(short_url):
    short_url = short_url.lower()
    if short_url[0] == "+":
        decoded_string = base36.loads(short_url)
        redirect_url = request.host
        with sqlite3.connect('urls.db') as conn:
            cursor = conn.cursor()
            select_row = """
                    SELECT URL FROM WEB_URL
                        WHERE ID=%s;
                    """ % (decoded_string)
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
                SELECT URL FROM WEB_URL WHERE keyword = '{short_url}';
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
        return render_template('error.html')


@app.template_filter('humantime')
def format_datetime(value, timeformat='%Y-%m-%d'):
    if value is None:
        return ""
    return time.strftime(timeformat, time.localtime(value))


@app.template_filter('shortcode')
def format_shortcode(value):
    """Return the base36 encoded short URL version of a number"""
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
