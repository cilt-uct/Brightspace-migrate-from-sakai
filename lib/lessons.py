# Classes and functions for Lessons conversion

import re
import os
import sys
import oembed
import requests
import logging
from bs4 import BeautifulSoup
from html import escape

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.utils import read_yaml
from lib.resources import get_content_displayname

# Lessons item types
# https://github.com/cilt-uct/sakai/blob/21.x/lessonbuilder/api/src/java/org/sakaiproject/lessonbuildertool/SimplePageItem.java#L36
class ItemType:
    RESOURCE = '1'
    PAGE = '2'
    ASSIGNMENT = '3'
    ASSESSMENT = '4'
    TEXT = '5'
    URL = '6'
    MULTIMEDIA = '7'
    FORUM = '8'
    COMMENTS = '9'
    STUDENT_CONTENT = '10'
    QUESTION = '11'
    BLTI = '12'
    PEEREVAL = '13'
    BREAK = '14'
    RESOURCE_FOLDER = '20'
    CHECKLIST = '15'
    FORUM_SUMMARY = '16'
    ANNOUNCEMENTS = '17'
    TWITTER = '18'
    CALENDAR = '19'

# https://regexr.com/3dj5t
YOUTUBE_RE = "^((?:https?:)?\/\/)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$"
YOUTUBE_PARAMS_RE = "t=([0-9]+)"

# https://stackoverflow.com/questions/4138483/twitter-status-url-regex
TWITTER_RE = "^https?:\/\/(www\.|m\.|mobile\.)?twitter\.com\/(?:#!\/)?\w+\/status?\/\d+"

def is_image(att, content_type):

    if content_type and content_type.startswith("image/"):
        return True

    extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.jfif', '.pjpeg', '.pjp', '.ico', '.cur',
                  '.tif', '.tiff', '.webp']
    path = att.lower()
    for ex in extensions:
        if path.endswith(ex):
            return True

    return False

def is_audio_video(APP, content_type, sakai_id):

    if content_type and content_type.startswith("video/"):
        return True

    if content_type and content_type.startswith("audio/"):
        return True

    return supported_media_type(APP, sakai_id)

def is_audio_url(url):

    audio_types = ("m4a", "mp3", "ogg", "flac", "wma", "wav")

    for atype in audio_types:
        if url.endswith(f".{atype}"):
            return True

    return False

def link_item(APP, content_type, sakai_id):

    if content_type in APP['lessons']['type_to_link']:
        # Matches a content type that we want to link
        return True
    else:
        # Matches an extension that we want to link
        for link_ext in APP['lessons']['ext_to_link']:
            if sakai_id.lower().endswith(f".{link_ext.lower()}"):
                return True

    return False

# Audio or video ile extensions we expect to have been imported into Media Library
def supported_media_type(APP, file_path):

    restricted_ext = read_yaml(APP['content']['restricted-ext'])
    supported_audio = restricted_ext['SUPPORTED_AUDIO']
    supported_video = restricted_ext['SUPPORTED_VIDEO']

    if "." in file_path:
        file_extension = file_path.split(".")[-1].upper()
        return (file_extension in supported_audio) or (file_extension in supported_video)

    return False

# Embed HTML for a youtube video with the given id
def youtube_embed(youtube_id, start_timestamp, title, desc):

    # These dimensions are slightly larger than the "Embed stuff" in Brightspace,
    # but match the Lessons sizing and are still within the RT editor width in Brightspace

    width = "640"
    height = "360"

    src_url = f"https://www.youtube.com/embed/{youtube_id}?feature=oembed&wmode=opaque&rel=0"

    if start_timestamp:
        src_url += f"&amp;start={start_timestamp}"

    allow_options = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    embed_iframe = f'<iframe width="{width}" height="{height}" src="{src_url}" frameborder="0" allow="{allow_options}" allowfullscreen="allowfullscreen" title="{title}"></iframe>'
    desc_html = f"<br>{escape(desc)}" if desc else ""

    return f'<p><span style="font-size: 19px;">{embed_iframe}</span>{desc_html}</p>'

def audio_embed(url, title):

    return f'<audio title="{escape(title)}" controls="controls"><source src="{url}"></audio>'

def twitter_embed(url, desc):

    consumer = oembed.OEmbedConsumer()
    endpoint = oembed.OEmbedEndpoint('https://publish.twitter.com/oembed', ['https://twitter.com/*'])
    consumer.addEndpoint(endpoint)
    response = consumer.embed(url)

    if response:
        embedJson = response.getData()
        if embedJson and 'html' in embedJson:
            embed_html = embedJson['html']
            if desc:
                embed_html += f"<p>{escape(desc)}</p>"
            return embed_html

    return None

def generic_iframe(url, desc):

    width = "640"
    height = "360"
    m = re.search('https?://([A-Za-z_0-9.-]+).*', url)
    if m:
        title = f"Web content from {m.group(1)}"
    else:
        title = "Web content"

    embed_link = f'<p><a href="{url}" target="_blank">Open in new window</a></p>'

    allow_options = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    embed_iframe = f'<iframe width="{width}" height="{height}" src="{url}" frameborder="0" allow="{allow_options}" allowfullscreen="allowfullscreen" title="{title}"></iframe>'
    desc_html = f"<br>{escape(desc)}" if desc else ""

    return f"{embed_link}{embed_iframe}{desc_html}"

def is_youtube(url):

    if re.search(YOUTUBE_RE, url):
        return True

    return False

def is_twitter(url):
    if re.search(TWITTER_RE, url):
        return True

    return False

def is_url_html(url):

    try:
        # Disable SSL cert validation
        url_head = requests.head(url, verify=False, allow_redirects=True, timeout = 30)

        if 'Content-Type' in url_head.headers:
            if url_head.headers['Content-Type'].startswith('text/html'):
                return True
    except Exception as e:
        logging.warning(f"Unable to connect to {url} to check content type: {str(e)}")

    return False

def parse_youtube(url):

    youtube_id = None
    start_time = None

    m1 = re.match(YOUTUBE_RE, url)
    youtube_id = m1.group(5)
    params = m1.group(6)

    if params:
        m2 = re.search(YOUTUBE_PARAMS_RE, params)
        if m2:
            start_time = m2.group(1)

    return (youtube_id, start_time)

# Embed a generic html fragment with some special handling
def generic_embed(html, desc):

    embed_html = html

    # Add twitter widgets which aren't included in the Lessons embed code
    if html.startswith('<blockquote class="twitter-tweet">'):
        embed_html += '<script async="" src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'

    if desc:
        embed_html += f"<p>{escape(desc)}</p>"

    return embed_html

# Embed a list of files in a Resources folder
def folder_list_embed(archive_path, collection_id, path_prefix, desc):

    with open(f"{archive_path}/content.xml", "r", encoding="utf8") as cp:
        content_soup = BeautifulSoup(cp, 'xml')

        # Find the collection
        print(f"Looking for {collection_id} in {archive_path}")
        html = '<div data-type="folder-list"><hr>'
        collection = content_soup.find("collection", id=collection_id)
        if not collection:
            print("Collection not found")
            return None

        # Collection title
        folder_displayname = get_content_displayname(archive_path, collection_id)
        folder_title = folder_displayname if folder_displayname else collection.get('rel-id')
        html += f"<p><b>{folder_title}</b></p>"

        # Find the files in the collection
        html += "<ul style='list-style-type: none;'>"
        resources = content_soup.find_all('resource')

        for resource in resources:
            parent_path = os.path.dirname(resource['id'])
            parent_directory = os.path.basename(os.path.normpath(collection_id))
            if parent_path.endswith(f'/{parent_directory}'):
                displayname = get_content_displayname(archive_path, resource['id'])
                file_name = displayname if displayname else resource["rel-id"]

                # TODO if this is a .URL, then resolve it and link directly
                if file_name != 'siteinfo.html':
                    href = f'{path_prefix}{resource["id"]}'
                    a_tag = f'<li><a href="{href}">{file_name}</a></li>'
                    html = html + a_tag

    if desc:
        html = html + f'</ul><hr><br>{escape(desc)}</div>'
    else:
        html = html + '</ul><hr></div>'

    return html

# Get the LTI launch URL from basiclti.xml for a content item

def get_archive_lti_link(archive_path, lti_content_id):

    with open(f"{archive_path}/basiclti.xml", "r", encoding="utf8") as blti:
        lti_soup = BeautifulSoup(blti, 'xml')

        # Find the collection
        lti_content = lti_soup.find("LTIContent", id=lti_content_id)
        if lti_content:

            lti_data = { }
            for param in ["launch", "custom", "description", "title", "contentitem"]:
                if lti_content.find(param) is not None:
                    lti_data[param] = lti_content.find(param).get_text()

            return lti_data

    # No launch URL found
    return
