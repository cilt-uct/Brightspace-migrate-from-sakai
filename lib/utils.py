import sys
import os
import re
import shutil
import copy
import json
import yaml
import zipfile
import bs4
import emails
import logging
import requests
import csv
import lxml.etree as ET
import unicodedata

from jinja2 import Environment, FileSystemLoader, select_autoescape
from bs4 import BeautifulSoup
from urllib.parse import urlparse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

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

    if not os.path.exists(file):
        return

    fin = open(file, "rt")
    data = fin.read()
    fin.close()

    # weird characters
    data = data.replace('\x1e', '').replace('&amp;#xb;' ,'').replace('&#xb;','').replace('&amp;#x2;' ,'').replace('&#x2;' ,'').replace('&#160;','').replace('&#11;','').replace('&amp;#x8;' ,'')
    data = data.replace('&amp;#x1;', '').replace('&#x1;' ,'').replace('&#x1e;' ,'').replace('&amp;#x1f;', '').replace('&#x1f;' ,'').replace('&amp;#x4;', '').replace('&#x4;' ,'')
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

    if not os.path.exists(file):
        return

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

def resolve_redirect(url):

    # Sakai shortened URLs like /x/ are resolved with redirects
    url_head = requests.head(url)

    if 'Location' in url_head.headers:
        return url_head.headers['Location']

    return None

# Get the canonical SIS course title for a course code and term from the courseinfo CSV file
def sis_course_title(APP, course, term):

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

def get_site_providers(APP, SITE_ID):

    site_folder = os.path.join(APP['archive_folder'], f"{SITE_ID}-archive/")
    site_tree = ET.parse(f'{site_folder}/site.xml')
    providers = [x.get('providerId') for x in site_tree.findall(".//provider")]

    return providers

def get_site_creator(APP, SITE_ID):

    site_folder = os.path.join(APP['archive_folder'], f"{SITE_ID}-archive/")

    site_tree = ET.parse(f'{site_folder}/site.xml')
    site = site_tree.find(".//site[@created-id]")
    creator_id = site.get("created-id")

    # Now lookup the eid from user.mxl
    user_tree = ET.parse(f'{site_folder}/user.xml')
    user = user_tree.find(f".//user[@id='{creator_id}']")
    creator_eid = user.get('eid') if user is not None else None

    return creator_eid

def get_user_by_email(APP, SITE_ID, email):

    site_folder = os.path.join(APP['archive_folder'], f"{SITE_ID}-archive/")

    user_tree = ET.parse(f'{site_folder}/user.xml')
    user = user_tree.find(f".//user[@email='{email}']")
    return user.get('eid') if user is not None else None


# Replace wiris with markup in an HTML blob
# Used in Lessons, T&Q, Q&A
# «math xmlns=¨http://www.w3.org/1998/Math/MathML¨»
#     «msqrt»
#         «mn»33«/mn»
#     «/msqrt»
# «/math»"
# <math title="" xmlns="http://www.w3.org/1998/Math/MathML" display="inline">
#     <semantics>
#         <mstyle>
#             <msqrt><mn>33</mn></msqrt>
#         </mstyle>
#     </semantics>
# </math>

def assert_valid_characters(s):
    for ch in s:
        if (unicodedata.category(ch)[0] == "C") and (ord(ch) not in (9, 10)):
            print(f"Invalid char: {ord(ch)} {ch}")
            raise Exception(f"invalid char {ord(ch)} in {s}")

def replace_wiris(html_str):

    html = BeautifulSoup(html_str, 'html.parser')

    for el in html.findAll("img", {"class" : "Wirisformula"}):
        math_ml_raw = el['data-mathml'].replace("«", "<").replace("»", ">").replace("¨", "\"").replace("§", "&")
        assert_valid_characters(math_ml_raw)
        math_ml = BeautifulSoup(math_ml_raw,'html.parser')
        el.replace_with(math_ml)

    return str(html)

# Used for relative URLs in Lessons and Site Info
def fix_unwanted_url_chars(currenturl, url_prefix):

    if not currenturl.startswith(url_prefix):
        return currenturl

    # parse url prefix, get path with https and path parsed_url.netloc + parsed_url.path
    parsed_url = urlparse(url_prefix)

    # remove the . but not replace the sakaiurl yet
    urlparts = [s.strip(".") for s in currenturl.split("/") if s != 'https:']
    joined_link = "/".join(urlparts).replace("/", "", 1)

    # replacements list below array(k,v)
    replacements = [
        (re.escape(parsed_url.netloc) + re.escape(parsed_url.path), ".."),
        ("%3A", ""),
        ("!", ""),
        (":",""),
        (re.escape("+"),"_")
    ]

    for key, value in replacements:
        joined_link = re.sub(key, value, joined_link)

    return joined_link

# Poll processes and log and remove those which have finished
def process_check(process_list):

    completed = []
    for p in process_list:
        p.poll()
        if p.returncode is not None:
            if p.returncode == 0:
                logging.info(f"Process {p.pid} terminated successfully with code 0")
            else:
                logging.error(f"Process {p.pid} terminated with code {p.returncode}")

            completed.append(p)

    for c in completed:
        process_list.remove(c)
