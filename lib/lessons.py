# Classes and functions for Lessons conversion

import re
import oembed
import requests
from html import escape

from lib.utils import *
from lib.resources import *

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
TWITTER_RE = "^https?:\/\/(www.|m.|mobile.)?twitter\.com\/(?:#!\/)?\w+\/status?\/\d+"

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
def youtube_embed(youtube_id, start_timestamp, title):

    # These dimensions are slightly larger than the "Embed stuff" in Brightspace,
    # but match the Lessons sizing and are still within the RT editor width in Brightspace

    width = "640"
    height = "360"

    src_url = f"https://www.youtube.com/embed/{youtube_id}?feature=oembed&wmode=opaque&rel=0"

    if start_timestamp:
        src_url += f"&amp;start={start_timestamp}"

    allow_options = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
    embed_iframe = f'<iframe width="{width}" height="{height}" src="{src_url}" frameborder="0" allow="{allow_options}" allowfullscreen="allowfullscreen" title="{title}"></iframe>'

    return f'<p><span style="font-size: 19px;">{embed_iframe}</span></p>'

def audio_embed(url, title):

    return f'<audio title="{escape(title)}" controls="controls"><source src="{url}"></audio>'

def twitter_embed(url):

    consumer = oembed.OEmbedConsumer()
    endpoint = oembed.OEmbedEndpoint('https://publish.twitter.com/oembed', ['https://twitter.com/*'])
    consumer.addEndpoint(endpoint)
    response = consumer.embed(url)

    if response:
        embedJson = response.getData()
        if embedJson and 'html' in embedJson:
            return embedJson['html']

    return None

def generic_iframe(url):

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

    return f"{embed_link}{embed_iframe}"


def is_youtube(url):

    if re.search(YOUTUBE_RE, url):
        return True

    return False

def is_twitter(url):
    if re.search(TWITTER_RE, url):
        return True

    return False

def is_url_html(url):

    # Disable SSL cert validation
    url_head = requests.head(url, verify=False, allow_redirects=True)

    if 'Content-Type' in url_head.headers:
        if url_head.headers['Content-Type'].startswith('text/html'):
            return True

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
def generic_embed(html):

    embed_html = html

    # Add twitter widgets which aren't included in the Lessons embed code
    if html.startswith('<blockquote class="twitter-tweet">'):
        embed_html += '<script async="" src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>'

    return embed_html

# Embed a list of files in a Resources folder
def folder_list_embed(archive_path, collection_id, path_prefix):

    with open(f"{archive_path}/content.xml", "r", encoding="utf8") as cp:
        content_soup = BeautifulSoup(cp, 'xml')

        # Find the collection
        print(f"Looking for {collection_id} in {archive_path}")
        html = '<div data-type="folder-list"><hr>'
        collection = content_soup.find("collection", id=collection_id)
        if not collection:
            print(f"Collection not found")
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
                if file_name != 'Site Information.html':
                    href = f'{path_prefix}{resource["id"]}'
                    a_tag = f'<li><a href="{href}">{file_name}</a></li>'
                    html = html + a_tag

    html = html + '</ul><hr></div>'

    return html
