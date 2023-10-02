# Classes and functions for Lessons conversion

import re
import oembed
import requests

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

    url_head = requests.head(url)

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
