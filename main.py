#!/usr/bin/env python
from flask import Flask, request, render_template, redirect
from sqlite3 import OperationalError
import sqlite3
import base36
import datetime, calendar

host = 'http://localhost:5000/'


def table_check():
    """Verify the tables exist in the db"""
    create_table = """
        CREATE TABLE "WEB_URL"(
        "ID" INTEGER PRIMARY KEY AUTOINCREMENT,
        "URL" TEXT NOT NULL,
        "owner" INTEGER DEFAULT 0,
        "createTime" INTEGER,
        "lastUsed" INTEGER,
        "hit" INTEGER DEFAULT 0,
        "keyword" TEXT
        );
        """
    with sqlite3.connect('urls.db') as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(create_table)
        except OperationalError:
            pass


app = Flask(__name__)


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
def home():
    if request.method == 'POST':
        original_url = request.form.get('url')
        keyword = request.form.get('keyword')
        if not original_url.startswith('http'):
            original_url = 'http://' + original_url
        timestamp = calendar.timegm(datetime.datetime.now().timetuple())
        with sqlite3.connect('urls.db') as conn:
            cursor = conn.cursor()
            if len(keyword) > 0:
                insert_row = """
                    INSERT INTO WEB_URL (URL, createTime, keyword)
                        VALUES ('%s', '%s', '%s')
                    """ % (original_url, timestamp, keyword)
            else:
                insert_row = """
                    INSERT INTO WEB_URL (URL, createTime)
                        VALUES ('%s', '%s')
                    """ % (original_url, timestamp)

            result_cursor = cursor.execute(insert_row)
            # Prepend the string with a + so we can differentiate between shortURL and custom Redirects
            encoded_string = "+" + base36.dumps(result_cursor.lastrowid)
        return render_template('home.html',
                               short_url=host + encoded_string,
                               keyword=keyword,
                               )
    return render_template('home.html')


@app.route('/<short_url>')
def redirect_short_url(short_url):
    short_url = short_url.lower()
    if short_url[0] == "+":
        decoded_string = base36.loads(short_url)
        redirect_url = 'http://localhost:5000'
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
    return redirect(redirect_url)




@app.route('/help')
def help():
    return render_template('help.html')
if __name__ == '__main__':
    # This code checks whether database table is created or not
    table_check()
    app.run(debug=True)
