#!/usr/bin/env python
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    g,
    Response,
    url_for
)
from flask_simpleldap import LDAP
from urllib.parse import urlparse
import base36
import datetime
import calendar
import time
import pugsql
import yaml
from pbr.version import VersionInfo

__version__ = VersionInfo('shorty').release_string()
__db_schema__ = 1

meta_info = {
    'version': __version__,
    'changelog': 'https://git.admin.franklin.edu/tins/shorty/raw/branch'
                 '/master/ChangeLog '
}


def get_config(configfile):
    try:
        with open(configfile, 'r') as config_file:
            config_entries = yaml.safe_load(config_file)
    except FileNotFoundError as error:
        print(error)
        return False
    else:
        config_data = config_entries
        return config_data


def uri_validator(uri):
    """ Determines if a given URL is valid and returns True/False"""
    # This code was obtained from a stackoverflow answer at:
    # https://stackoverflow.com/questions/7160737/python-how-to-validate-a-url-in-python-malformed-or-not
    try:
        result = urlparse(uri)
        return all([result.scheme, result.netloc, result.path])
    except Exception:
        return False


def update_schema(old, new):
    print(f'Performing updates for {old} to {new}')


def table_check():
    """Verify the tables exist in the db"""
    try:
        installed_schema = queries.get_version_number()['schema_version']
    except Exception as e:
        print(e)
        print('in exception, starting at 0')
        installed_schema = 0

    if installed_schema < __db_schema__:
        update_schema(installed_schema, __db_schema__)
    elif installed_schema == 0:
        create_tables()
    else:
        print('Schema version is current, no migration needed')


def create_tables():
    try:
        if config['db']['string'].startswith('sqlite'):
            queries.create_version_table()
            queries.create_owner_table()
            queries.create_namespace_table()
            queries.create_permission_table()
            queries.create_namespacepermission_table()
            queries.create_redirect_table()
            queries.create_apppermission_table()
        elif config['db']['string'].startswith('mysql'):
            queries.my_create_version_table()
            queries.my_create_owner_table()
            queries.my_create_namespace_table()
            queries.my_create_permission_table()
            queries.my_create_namespacepermission_table()
            queries.my_create_apppermission_table()
            queries.my_create_redirect_table()
        queries.insert_default_permissions()
        queries.insert_default_namespaces()
    except Exception as e:
        print(e)
        pass


app = Flask(__name__)
config = get_config('/home/kellya/projects/shorty/conf/conf.yaml')
queries = pugsql.module(config['app']['sql_dir'])
queries.connect(config['db']['string'])

ldap_vars = [
    'LDAP_HOST',
    'LDAP_BASE_DN',
    'LDAP_USERNAME',
    'LDAP_PASSWORD',
    'LDAP_REALM_NAME',
    'LDAP_USER_OBJECT_FILTER',
]
app.config['LDAP_REALM_NAME'] = config['ldap']['realm_name']
app.config['LDAP_HOST'] = config['ldap']['host']
app.config['LDAP_BASE_DN'] = config['ldap']['base_dn']
app.config['LDAP_USERNAME'] = config['ldap']['username']
app.config['LDAP_PASSWORD'] = config['ldap']['password']
app.config['LDAP_OPENLDAP'] = True
app.config['LDAP_USER_OBJECT_FILTER'] = config['ldap']['user_object_filter']
ldap = LDAP(app)


def hit_increase(record_id, namespace=1):
    """
    Updates the hit count and last used timestamp for record_id
    :param record_id: int or string specifying a unique record
    :param namespace: int representing the namespace id
    :return: None
    """
    timestamp = calendar.timegm(datetime.datetime.now().timetuple())
    if type(record_id) == str:
        # We need to get the ID for the shortname/keyword
        record_id = queries.get_record_by_keyword(keyword=record_id,
                                                  namespace=namespace)['id']

    queries.update_redirect_hits(lastUsed=timestamp, recordid=record_id)


def get_userid(username):
    """
    Returns the numeric ID of the username given or False if no user matches
    :param username:
    :return: int
    """
    try:
        userid = queries.get_id_from_name(username=username)['id']
        return userid
    except Exception:
        return False


def set_default_permissions(username):
    print(username)
    """
    Create default permission set for a user if they are not already in the db
    :param username:UID from LDAP
    :return:  None
    """
    queries.create_owner_entry(username=username)
    userid = get_userid(username)
    queries.create_owner_default_permissions(owner=userid)
    queries.create_user_space_default_permissions(owner=userid)


def get_permissions(username):
    """
    Gets user permissions from db, or creates a default value if user
    isn't already in the DB
    :param username: uid from LDAP
    :return: A dictionary containing permissions as returned from the DB
    """
    userid = get_userid(username)
    permissions = []
    if not userid:
        # if we don't have a username from the db, it's a new user,
        # so create it and call back
        set_default_permissions(username)
        get_permissions(username)
    for permission in queries.get_user_permissions(owner=userid):
        permissions.append(permission['name'])
    return permissions


def get_namespace_permissions(username):
    """
    Returns dictionary of namespaces to which the specified username has access
    :param username:
    :return:
    """
    userid = get_userid(username)
    return_val = []
    for row in queries.get_namespace_permissions(owner=userid):
        return_val.append(row)
    return return_val


def get_uri_path(namespace_id, keyword, username=None):
    namespace = queries.get_namespace_by_id(id=namespace_id)['name']

    reserved_names = {
        'user': username,
        'global': '/'
    }
    if not namespace.lower() in reserved_names:
        return f'/{namespace.lower()}/{keyword.lower()}'
    elif namespace.lower() == 'global':
        return f'/{keyword}'
    elif namespace == 'user' and keyword:
        return f'/~{username.lower()}/{keyword}'
    elif namespace == 'user' and not username:
        return False, "Username must be specified with user namespace"
    else:
        return False, "There was an error processing this url"


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
    permissions = get_permissions(username)
    ns_permissions = get_namespace_permissions(username)
    if request.method == 'POST':
        original_url = request.form.get('url')
        keyword = request.form.get('keyword')
        if not original_url.startswith('http'):
            original_url = 'http://' + original_url
        if not uri_validator(original_url):
            errors.append(f'URL {original_url} is not in the proper format')
        try:
            if len(keyword) > 0 and not keyword.isalnum():
                errors.append('Keyword must only contain alpha-numeric '
                              'characters.')
        except TypeError:
            # If we weren't given a keyword, just pass
            pass
        try:
            has_keyword = True if len(keyword) > 0 else False
        except TypeError:
            has_keyword = False
        if request.form.get('namespace') and has_keyword:
            namespace = request.form.get('namespace')
        else:
            namespace = 2
        if not queries.search_keyword(owner=userid, namespace=namespace,
                                      keyword=keyword)['count'] == 0:
            errors.append(f'Keyword {keyword} is not unique in specified '
                          'namespace')
        if len(errors) == 0:
            timestamp = calendar.timegm(datetime.datetime.now().timetuple())
            if has_keyword:
                last_row_id = queries.insert_redirect_keyword(
                    url=original_url,
                    owner=userid,
                    createTime=timestamp,
                    keyword=keyword,
                    namespace=namespace,
                )
            else:
                last_row_id = queries.insert_redirect(
                    url=original_url,
                    owner=userid,
                    createTime=timestamp,
                    namespace=namespace
                )
            encoded_string = "+" + base36.dumps(last_row_id)
            # Prepend the string with a + so we can differentiate between
            # shortURL and custom Redirects
            url_base = f'{request.scheme}://{request.host}' or None
            if has_keyword:
                keyword_url = url_base + get_uri_path(
                    namespace,
                    keyword,
                    username
                )
            else:
                keyword_url = None
            return render_template('home.html',
                                   url_base=url_base,
                                   short_url=encoded_string,
                                   keyword=keyword,
                                   errors=errors,
                                   metainfo=meta_info,
                                   permissions=permissions,
                                   ns_permissions=ns_permissions,
                                   keyword_url=keyword_url,
                                   )
    return render_template(
        'home.html',
        errors=errors,
        metainfo=meta_info,
        permissions=permissions,
        ns_permissions=ns_permissions
    )


@app.route('/_help')
def show_help():
    """
    Displays the help page
    :return: jinja template for help.html
    """
    url_base = f'{request.scheme}://{request.host}' or None
    return render_template(
        'help.html',
        url_base=url_base,
        metainfo=meta_info,
        permissions=[]
    )


@app.route('/_logout')
def logout():
    """
   Haphazardly handles a logout action for a basic authentication, which isn't
   really a thing for basic-auth
    :return:
    """
    return Response(
        'User Logout',
        401,
        {'WWW-Authenticate': f'Basic realm="{config["ldap"]["realm_name"]}"'}
    )


@app.route('/_mylinks', methods=['GET'])
@ldap.basic_auth_required
def my_links():
    username = g.ldap_username
    """
    Displays all the links created by the logged-in user
    :return: jinja template render for links.html
    """
    permissions = get_permissions(username)
    try:
        success = request.args['editsuccess']
    except Exception:
        success = False
    results = queries.get_shortcuts(owner=get_userid(username))
    return render_template(
        'links.html',
        results=results,
        metainfo=meta_info,
        permissions=permissions,
        username=username,
        editsuccess=success
    )


@app.route('/_edit', methods=['GET', 'POST'])
@ldap.basic_auth_required
def edit_link():
    username = g.ldap_username
    updateurl = request.form.get('url')
    permissions = get_permissions(username)
    userid = get_userid(username)

    if request.method == 'GET':
        recordid = base36.loads(request.args.get('id'))
        url = queries.get_record_by_id_with_owner(owner=userid,
                                                  id=recordid)['url']
        try:
            return render_template('edit.html', url=url, metainfo=meta_info,
                                   permissions=permissions)
        except IndexError:
            return render_template('edit.html', url='', metainfo=meta_info,
                                   permissions=permissions,
                                   errors=['No permission to edit this ID'])
    elif request.method == 'POST':
        queries.update_redirect(updateurl=updateurl, owner=userid,
                                id=request.args.get('id'))
        return redirect(url_for('my_links', editsuccess=True))


@app.route('/_admin')
@ldap.basic_auth_required
def admin():
    permissions = get_permissions(g.ldap_username)
    return render_template(
        'admin.html',
        permissions=permissions,
        metainfo=meta_info
    )


@app.route('/<namespace>/<keyword>')
def redirect_name_keyword(namespace, keyword):
    """
    Name-based keywords so that users can create their own redirects that don't
    overwrite globals
    :param namespace:
    :param keyword:
    :return:
    """
    if not namespace[0] == '~':
        namespace = queries.get_namespace_id_by_name(name=namespace)['id']
        hit_increase(keyword, namespace)
        redirect_url = queries.get_namespace_redirect(
            namespace=namespace,
            keyword=keyword,
        )

    else:
        ownerid = get_userid(namespace[1:])
        redirect_url = queries.get_user_namespace_redirect(owner=ownerid,
                                                           keyword=keyword)
        hit_increase(keyword, 2)

    if redirect_url:
        redirect_url = redirect_url['url']
    else:
        return "The shortlink specified is invalid"

    return redirect(redirect_url)


@app.route('/<short_url>')
def redirect_short_url(short_url):
    """
    Handles shortlink/keyword redirects by pulling the destination from the DB
    matching a base36 encoded version of the shortlink, or a /keyword link if
    the short_url does not start with a +
    :param short_url:
    :return:
    """
    short_url = short_url.lower()
    redirect_url = ""
    if short_url[0] == "+":
        decoded_string = base36.loads(short_url)
        try:
            redirect_url = queries.get_redirect_url(id=decoded_string)['url']
            hit_increase(decoded_string)
        except Exception as e:
            print(e)
    else:
        print(short_url)
        redirect_url = queries.get_redirect_keyword_ns(keyword=short_url,
                                                       namespace=1)['url']
        hit_increase(short_url, namespace=1)
    try:
        return redirect(redirect_url)
    except Exception:
        permissions = []
        return render_template(
            'error.html',
            metainfo=meta_info,
            permissions=permissions,
            url=short_url
        )


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
