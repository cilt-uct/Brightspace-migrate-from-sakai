import sys
import os
import re
import shutil
import copy
import json
import yaml
import numpy as np
import zipfile
import bs4
import emails
import logging
import time
import requests
import subprocess
import csv

from datetime import datetime, timedelta
from emails.template import JinjaTemplate as T
from jinja2 import Environment, FileSystemLoader, select_autoescape
from validate_email import validate_email
from bs4 import BeautifulSoup
from pathlib import Path

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.jira_rest import MyJira
from lib.local_auth import getAuth

class myFile(object):
    def __init__(self, filename):
        self.f = open(filename)

    def read(self, size=None):
        return self.f.next()

# init soup based on filename passed
def init__soup(site_folder, file):
    file_path = os.path.join(site_folder, file)

    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf8") as fp:
            return BeautifulSoup(fp, 'xml')
    else:
        return None

def has_doctype(soup):
    items = [item for item in soup.contents if isinstance(item, bs4.Doctype)]
    return items[0] if items else None

def unique(list1):
    x = np.array(list1)
    return np.unique(x).tolist()

## Current Templates:
#   - styled : [DEFAULT] includes styles, and scripts
#   - small  : includes just style
def make_well_formed(html, title = None, template = "styled"):

    new_html = copy.copy(html)

    has_head = new_html.head
    has_body = new_html.body

    with open(f'{parent}/templates/{template}.html', 'r') as f:
        tmpl_contents = f.read()

    tmpl = BeautifulSoup(tmpl_contents, 'html.parser')

    # remove the style elements from the given HTML - we will add to the head later
    style_tag = new_html.new_tag("style")
    for s in new_html.find_all('style'):
        style_tag.append(s.text)
        s.decompose()

    if (has_head is None) and (has_body is None):
        # no HTML structure so use the template

        if (title is not None):
            title_tag = tmpl.new_tag("title")
            title_tag.append(title)
            tmpl.head.append(title_tag) # insert title tag

        col = tmpl.body.find("div", class_="col-sm-10 offset-sm-1")
        col.append(new_html)
        new_html = copy.copy(tmpl)

    if (has_head is not None):
        # remove previous meta, title and style links
        for rm in new_html.head.find_all(['meta','title','link']):
            rm.decompose()

        # add the appropriate meta and style links
        for tag in tmpl.head.find_all(['meta','link']):
            new_html.head.append(tag)

        if (title is not None):
            title_tag = tmpl.new_tag("title")
            title_tag.append(title)
            new_html.head.append(title_tag) # insert title tag

    if (has_body is not None):
        xpath = new_html.select('body > div[class="container-fluid"] > div[class="row"] > div[class="col-sm-10 offset-sm-1"]')

        if (len(xpath) == 0):
            # ok so the columns are not there - lets add it then

            container_tag = html.new_tag('div', **{"class":"container-fluid"})
            row_tag = new_html.new_tag('div', **{"class":"row"})
            col_tag = new_html.new_tag('div', **{"class":"col-sm-10 offset-sm-1"})

            row_tag.append(col_tag)
            container_tag.append(row_tag)

            body_children = list(html.body.children)

            new_html.body.clear()
            new_html.body.append(container_tag)

            for child in body_children:
                col_tag.append(child)

    new_html.head.append(style_tag) # insert current style elements into the head of new html

    return new_html

def remove_unwanted_characters(file):

    fin = open(file, "rt")
    data = fin.read()
    fin.close()

    # weird characters
    data = data.replace('\x1e', '').replace('&amp;#xb;' ,'').replace('&#xb;','').replace('&amp;#x2;' ,'').replace('&#x2;' ,'').replace('&#160;','').replace('&#11;','').replace('&amp;#x8;' ,'')
    data = data.replace('&amp;#x1;', '').replace('&#x1;' ,'').replace('&amp;#x1f;', '').replace('&#x1f;' ,'').replace('&amp;#x4;', '').replace('&#x4;' ,'')
    data = data.replace('&amp;#x7;', '').replace('&#x7;' ,'')

    # newline and tab
    data = data.replace('&#xa;', '').replace('&#x9;', ' ')

    # character replacement
    data = data.replace('&#14;','ffi').replace('&#12;','fi')

    # https://www.learnbyexample.org/python-string-isspace-method/
    data = data.replace(u"\u00A0", " ").replace(u"\u0020", " ").replace(u"\u2003", " ").replace(u"\u2009", " ").replace(u"\u200A", " ").replace(u"\u202F", " ").replace(u"\u205F", " ").replace(u"\u3000", " ")

    # Escaped unicode in json in Lessons item attributes: vertical tab and left and right single quotes
    data = data.replace("\\u000B", "").replace("\\u2018", "'").replace("\\u2019", "'")

    # replace freestanding & with &amp;
    data = re.sub('\s&\s', '$amp;', data)

    # replace one-or-more spaces/non-breaking-spaces with a single space
    # data = re.sub(r'\s+', ' ', data)

    fin = open(file, "wt")
    fin.write(data)
    fin.close()

def remove_unwanted_characters_html(data):

    data = data.replace('&#x2;','').replace('&#xb;','')
    return data

def remove_unwanted_characters_tq(file):

    fin = open(file, "rt")
    data = fin.read()
    fin.close()

    # weird characters
    data = data.replace('&#11;','').replace(u"\u000B",'')

    fin = open(file, "wt")
    fin.write(data)

def write_test_case(html, id):
    print(f"{parent}/tmp-{id}.html")
    with open(f"{parent}/tmp-{id}.html", "w", encoding = 'utf-8') as file:
        file.write(str(html.prettify()))

def create_folders(dir_, clean = False):
    if clean:
        if os.path.exists(dir_):
            shutil.rmtree(dir_)

    if not os.path.exists("{}".format(dir_)):
        return os.makedirs("{}".format(dir_))

    return True

def get_size(filename):
    if not os.path.exists(filename):
        return None

    return os.path.getsize(filename)

def format_bytes(size):
    # 2**10 = 1024
    power = 2**10
    n = 0
    power_labels = {0 : ' B', 1: ' KB', 2: ' MB', 3: ' GB', 4: ' TB'}
    while size > power:
        size /= power
        n += 1
    return r'{:.1f}{}'.format(size, power_labels[n])

def read_yaml(file_path):
    with open(file_path, "r") as f:
        return yaml.safe_load(f)

def get_config():
    return read_yaml("{}/config/config.yaml".format(parent))

def get_log(filename):
    _file = open(filename, "r")
    lines = _file.readlines()
    _file.close()

    # clean up the array - remove new lines
    lines = list(map( lambda s: s.replace('\n',''), lines ))

    # remove empty lines in log file
    return json.dumps(list(filter(lambda s: len(s) > 3, lines)))

def zipfolder(zip_file, path):

    # 'w' - Opens a file for writing. Creates a new file if it does not exist or 're-creates' the file if it exists.
    # Use zipfile.ZIP_STORED rather than zipfile.ZIP_DEFLATED because most large files are video which are compressed anyway
    zipobj = zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_STORED)

    for base, dirs, files in os.walk(path):
        for file in files:
            fn = os.path.join(base, file)

            if file.endswith("old"):
                continue

            # Compress XML and smaller assets under 250M, otherwise store
            if "xml" in file or os.path.getsize(fn) < (250*1024*1024):
                zipobj.write(fn, fn.replace(path,''), compress_type = zipfile.ZIP_DEFLATED)
            else:
                zipobj.write(fn, fn.replace(path,''), compress_type = zipfile.ZIP_STORED)

    zipobj.close()

    return True


def create_jira(APP, url, site_id, site_title, jira_state, jira_log, failure_type: str = None, failure_detail: str = None, user: str = None):
    now = datetime.now()
    jira_date_str = now.strftime("%a, %-d %b %-y %H:%M")

    try:
        jira_log = json.loads(jira_log)
        if APP['jira']['last'] > 0:
            N = APP['jira']['last']
            jira_log = jira_log[-N:]
    except (TypeError, ValueError):
        pass

    if isinstance(jira_log, list):
        jira_log_str = "\n".join(jira_log)
    else:
        jira_log_str = jira_log

    sakai_url = APP['sakai_url']
    site_msg = f'+SITE:+ {site_id}\n'
    link_msg = f'+LINK:+ {sakai_url}/portal/site/{url}\n'
    fail_type_msg = f'+FAILURE TYPE:+ {failure_type}\n'
    fail_detail_msg = f'+FAILURE DETAIL:+ {failure_detail}\n'
    started_by = f'+STARTED-BY:+ {user if user else "Unknown"}\n\n'
    log_msg = f'+LOG:+\n{{noformat}}\n{jira_log_str}\n{{noformat}}'

    with MyJira() as j:
        fields = {
            'project': {'key': APP['jira']['key']},
            'summary': "{} {} {} {}".format(APP['jira']['prefix'], site_title, jira_date_str, " [Expired]" if jira_state == 'expire' else ''),
            'description': site_msg + link_msg + fail_type_msg + fail_detail_msg + started_by + log_msg,
            'issuetype': {'name': 'Task'},
            'assignee': {'name': APP['jira']['assignee']},
            'customfield_10001': str(site_id),
            'labels': []
        }

        if jira_state == 'expire':
            fields['labels'].append('expire')
            del fields["assignee"]

        if site_id in url:
            fields['labels'].append('self-service')

        if j.createIssue(fields) is not None:
            return True

    return False


def rewrite_tool_ref(tool_xml_path, find_id, replace_id):

    if not os.path.exists(tool_xml_path):
        logging.warning(f"Tool path {tool_xml_path} not found")
        return False

    # We don't know the XML structure here so do a naive string replace
    fin = open(tool_xml_path, "rt")
    data = fin.read()
    fin.close()

    if find_id in data:
        data = data.replace(find_id, replace_id)
        fin = open(tool_xml_path, "wt")
        fin.write(data)
        fin.close()
        return True

    return False

def send_template_email(APP, template, to, subj, **kwargs):
    """Sends an email using a template."""

    logging.info(f"Sending template email {template} with args: {kwargs}")

    subject = Environment().from_string(subj)

    env = Environment(
        loader=FileSystemLoader(APP['email']['path']),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template(template)

    kwargs['subject'] = subject.render(**kwargs)

    if 'started_by' in kwargs:
        if kwargs['started_by']:
            if to:
                to += ';' + kwargs['started_by']
            else:
                to = kwargs['started_by']

    if to:
        return send_email(APP['helpdesk-email'], to.split(';'), kwargs['subject'], template.render(**kwargs))
    else:
        logging.warn(f"No recipient address for mail with subject {kwargs['subject']}")
        return True

    return None

def send_email(mail_from, to, subj, body):
    """Sends an email."""
    # Send the finalized email here.
    #print (to)
    #print (subj)
    #print (body)

    logging.debug(f"Sending email from {mail_from} to {to} subject {subj}")

    message = emails.html(subject=subj,
                      html=body,
                      mail_from=mail_from)

    return message.send(to=to)

def stripspace(orig):
    new = orig.replace("\n", " ").replace("\t", " ")
    while "  " in new:
        new = new.replace("  ", " ")

    return new

# Call middleware API and return JSON response with optional retries
def middleware_api(APP, url, payload_data = None, retries = None, retry_delay = None, method = None):

    tmp = getAuth(APP['auth']['middleware'])
    if (tmp is not None):
        AUTH = {'host' : tmp[0], 'user': tmp[1], 'password': tmp[2]}
    else:
        raise Exception("Middleware Authentication required")

    if retries is None:
        retries = APP['middleware']['retries']

    if retry_delay is None:
        retry_delay = APP['middleware']['retry_delay']

    logging.debug(f"Calling endpoint {url} retries {retries} delay {retry_delay}")

    retry = 0
    json_response = None
    last_status = None

    while (retry <= retries):

        try:
            if payload_data is not None:
                if method == 'PUT':
                    response = requests.put(url, data=payload_data, auth=(AUTH['user'], AUTH['password']))
                else:
                    response = requests.post(url, data=payload_data, auth=(AUTH['user'], AUTH['password']))
            else:
                response = requests.get(url, auth=(AUTH['user'], AUTH['password']))

            last_status = response.status_code

            if last_status == 401:
                logging.error(f"API call {url} is Unauthorized")
                return {'status': 'ERR', 'data': 'Unauthorized'}

            if (last_status < 500) and '{' in response.text and '}' in response.text:
                # Succeeded
                json_response = response.json()
                return json_response
            else:
                logging.warning(f"{url} returned {last_status}: '{response.text}'")

            # retry
            retry += 1
            if (retry <= retries):
                logging.warning(f"Retry {retry} for call to {url} after response code {last_status}")
                time.sleep(retry_delay)

        except Exception as err:
            logging.exception(err)
            retry += 1
            if (retry <= retries):
                logging.warning(f"Retry {retry} for call to {url} after exception")
                time.sleep(retry_delay)

    logging.error(f"API call {url} failed: {last_status} {json_response}")
    return None


def enroll_in_site(APP, eid, import_id, role):

    enroll_user_url = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['enroll_user_url'])

    logging.info(f"enroll_in_site: {import_id} {eid} using endpoint {enroll_user_url}")
    json_response = middleware_api(APP, enroll_user_url, payload_data={'org_id': import_id, 'eid': eid, 'role': role})

    if json_response is not None and 'data' in json_response and 'UserId' in json_response['data']:
        user_id = json_response['data']['UserId']
        logging.info(f"Enrolled username {eid} userid {user_id} in {import_id}")
        return True

    if json_response is not None and 'status' in json_response and 'NotFound' in json_response['status']:
        logging.warning(f"Ignoring enrolment for {eid}, not found in Brightspace")
        return True

    # {'data': 'User NNN (###) is Inactive', 'status': 'ERR'}
    valid_return = json_response is not None
    status_error = valid_return and 'status' in json_response and json_response['status'] == 'ERR' and 'data' in json_response
    user_inactive = status_error and 'is Inactive' in json_response['data']
    user_not_found = status_error and 'User not found' in json_response['data']

    if user_not_found:
        logging.warning(f"Ignoring enrolment for {eid}, user not found in Brightspace")
        return True

    if user_inactive:
        logging.warning(f"Ignoring enrolment for {eid}, user is inactive in Brightspace")
        return True

    raise Exception(f"Could not enroll user {eid} in {import_id}: {json_response}")

def find_user_and_enroll_in_site(APP, eid, import_id, role):

    # middleware now supports enrolment via eid directly, so no need to search
    return enroll_in_site(APP, eid, import_id, role)

def get_var(varname):
    base = Path(os.path.dirname(os.path.abspath(__file__))).parent / 'base.sh'

    CMD = f'echo $(source {base}; echo $%s)' % varname
    p = subprocess.Popen(CMD, stdout=subprocess.PIPE, shell=True, executable='/bin/bash')
    return p.stdout.readlines()[0].strip().decode("utf-8")

def web_login(login_url, username, password):

    logging.info(f"Web UI login with service account {username}")

    values = {
        'web_loginPath': '/d2l/login',
        'username': username,
        'password': password
    }

    session = requests.Session()
    session.post(login_url, data=values, timeout=30)
    return session

def resolve_redirect(url):

    # Sakai shortened URLs like /x/ are resolved with redirects
    url_head = requests.head(url)

    if 'Location' in url_head.headers:
        return url_head.headers['Location']

    return None

def course_title(APP, course, term):

    import csv

    # AAE2001F,2024,"Special Study Module",AAE,2024-01-02,2024-06-12
    fieldnames = ['course', 'term', 'title', 'dept', 'start', 'end']
    csv_src = APP['courseinfo']

    with open(csv_src, newline='') as csvfile:
        fieldnames = ['course', 'term', 'title', 'dept', 'start', 'end']
        reader = csv.DictReader(csvfile, fieldnames = fieldnames)
        for row in reader:
            if row['course'] == course and row['term'] == term:
                return row['title']

    return

def site_has_tool(APP, SITE_ID, tool_id):

    site_folder = os.path.join(APP['archive_folder'], f"{SITE_ID}-archive/")
    site_soup = init__soup(site_folder, "site.xml")

    if site_soup.find("tool", {"toolId": tool_id}):
        return True

    return False
