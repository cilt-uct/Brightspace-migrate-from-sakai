import argparse
import os
import sys
import pprint
import json
import base64
from jsonpath_ng.ext import parse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *
from lib.lessons import *
from lib.resources import *

API_VERSION="1.67"

# See https://docs.valence.desire2learn.com/res/content.html

# Get an HTML page directly from Brightspace
def get_lessons_html(url, session):
    r = session.get(url, timeout=30)

    # Set the encoding explicitly
    r.encoding="UTF-8"

    return r.text if r.status_code == 200 else None

# Returns ToC as JSON: https://docs.valence.desire2learn.com/res/content.html#get--d2l-api-le-(version)-(orgUnitId)-content-toc
def get_toc(base_url, org_id, session):
    api_url = f"{base_url}/d2l/api/le/{API_VERSION}/{org_id}/content/toc"
    print(f"TOC from: {api_url}")
    r = session.get(api_url, timeout=30)
    return r.text if r.status_code == 200 else None

# Get the media ID for a given audio or video path
# Match the filename in the Structure of the unit with the given parent id,
# and then find the video URL in topics
def get_media_id(content_toc, file_path, displayname):

    print(f"get_media_id for {file_path}")

    resource_node = list(filter(lambda x: x['Title'] == 'Resources', content_toc['Modules']))[0]
    toplevel_lessons = list(filter(lambda x: x['Title'] not in ('Resources','External Resources'), content_toc['Modules']))

    media_paths = []

    # Sakai ID: /group/42190a5a-3b44-4eda-9fb9-83773b4f6410/
    if not file_path.startswith("/group/"):
        raise Exception(f"Unexpected path: {file_path}")

    media_paths = file_path.split('/')[3:]
    print(f"paths: {media_paths}")

    filename = displayname if displayname is not None else media_paths[-1]

    print(f"Filename: {filename}")

    media_id = None
    topic_id = None
    media_url = None

    # Find the media_id. First try to match on title in Lessons, if it's unique in the site.
    jpe_cs = f"$..Topics[?(@.Title='{filename}')]"
    jpe_files = parse(jpe_cs)
    topics = jpe_files.find(toplevel_lessons)

    topic_match = list(filter(lambda x: x.value['TypeIdentifier'] == 'ContentService', topics))

    if len(topic_match)==1:
        print(f"Unique match for {filename}")
        media_url = topic_match[0].value['Url']
    else:
        # See if the name is unique in the Resources tree
        topics = jpe_files.find(resource_node)
        topic_match = list(filter(lambda x: x.value['TypeIdentifier'] == 'ContentService', topics))

        if len(topic_match)==1:
            print(f"Unique match for {filename}")
            media_url = topic_match[0].value['Url']
        else:
            # Find it another way
            print(f"Multiple matches: traversing path {file_path}" if topic_match else f"No match in Lessons modules: looking in Resources for {file_path}")

            # The Sakai path contained in the id may not match the Resources tree directly,
            # because of display names and/or changes to folder names made by the Brightspace importer.

            for path in media_paths:
                if path == filename:
                    # We're at the end, so look for an activity
                    topic = list(filter(lambda x: x['TypeIdentifier'] == 'ContentService' and x['Title'] == filename, resource_node['Topics']))[0]
                    media_url = topic['Url']
                    media_id = media_url.split(':')[-1].split('/')[0]
                    break
                else:
                    # TODO use the folder display  name
                    module_search = list(filter(lambda x: x['Title'] == path, resource_node['Modules']))

                    if module_search:
                        print(f"Moving down to {path}")
                        resource_node = module_search[0]
                    else:
                        # Is it unique at this level?
                        print(f"Checking uniqueness for last time, no match for '{path}'")
                        topics = jpe_files.find(resource_node)
                        topic_match = list(filter(lambda x: x.value['TypeIdentifier'] == 'ContentService', topics))
                        if not topic_match:
                            raise Exception(f"Path element '{path}' from '{file_path}' not found in Resources module in ToC")

                        if len(topic_match)==1:
                            print(f"Unique match for {filename}")
                        else:
                            print(f"Using first match of {len(topic_match)} for {filename}")
                            logging.warning(f"Using non-unique match for {filename} in {file_path} for media id")

                        media_url = topic_match[0].value['Url']
                        break

    if not media_url:
        raise Exception("Cannot find media url for {filename}")

    # Audio or video content service media Url
    media_id = media_url.split(':')[-1].split('/')[0]

    print(f"media_id is: {media_id} from {media_url}")

    return media_id

# Find the topic ID by matching on the URL for the underlying html file which is
# named from the Sakai Lessons ID by the Brightspace import code. So this is
# guaranteed to match immediately after the import.

def get_topic_id(content_toc, topic_path):

    toplevel_lessons = list(filter(lambda x: x['Title'] not in ('Resources','External Resources'), content_toc['Modules']))

    jpe = f"$..Topics[?(@.Url=='{topic_path}')]"
    jsonpath_expression = parse(jpe)
    topic_matches = jsonpath_expression.find(toplevel_lessons)

    if not topic_matches:
        # pprint.pprint(toplevel_lessons, indent=3)
        # raise Exception(f"No topic found with URL matching {topic_path}")
        # TODO
        return None

    for match in topic_matches:
        topic_id = match.value['TopicId']

    return topic_id


def run(SITE_ID, APP, import_id, transfer_id):

    logging.info('Replace placeholders with multimedia links for import_id: {}'.format(import_id))

    # Check that there are placeholders in this site

    site_folder = APP['archive_folder']
    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(site_folder, SITE_ID)
    remove_unwanted_characters(xml_src)
    file_path = os.path.join(site_folder, xml_src)

    # Find the Lessons items that contain placeholders and/or audio/video links

    placeholder_items = []

    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        items = soup.find_all('item', attrs={"type": "5"})
        for item in items:
            html = BeautifulSoup(item['html'], 'html.parser')
            found = False

            # At least one placeholder
            if html.find('p', attrs={"data-type": "placeholder"}):
                placeholder_items.append(item['id'])
                continue

            # Or at least one link to an audio or video file
            for link in html.find_all('a'):
                href = link.get('href')
                if href and href.startswith("../") and supported_media_type(APP, href):
                    print(f"item {item.get('id')} title '{item.get('title')}' has a relevant link: {href}")
                    placeholder_items.append(item['id'])
                    break

            # Or embedded audio or video (AMA-612)
            for link in html.find_all(['audio', 'video']):

                src = link.get('src')
                if not src:
                    source = link.find('source')
                    if source:
                        src = source.get('src')

                if src and src.startswith("../"):
                    print(f"item {item.get('id')} title '{item.get('title')}' has an embedded HTML5 audio or video link: {src}")
                    placeholder_items.append(item['id'])
                    break

    if not placeholder_items:
        logging.info("No placeholders or audio/video links in Lessons content")
        return

    # Login to fetch files directly
    webAuth = getAuth('BrightspaceWeb')
    if (webAuth is not None):
        WEB_AUTH = {'username': webAuth[0], 'password' : webAuth[1]}
    else:
        raise Exception(f'Web Authentication required [BrightspaceWeb]')

    brightspace_url = APP['brightspace_url']

    login_url = f"{brightspace_url}/d2l/lp/auth/login/login.d2l"
    brightspace_session = web_login(login_url, WEB_AUTH['username'], WEB_AUTH['password'])
    brightspace_last_login = datetime.now()

    # Get the ToC
    content_toc = json.loads(get_toc(brightspace_url, import_id, brightspace_session))
    print("#### TOC ####")

    #pprint.pprint(content_toc, width=sys.maxsize)
    #print(json.dumps(content_toc, indent=3))

    content_defaultpath = content_toc['Modules'][0]['DefaultPath']
    topic_prefix = f"{content_defaultpath}LessonBuilder/"

    #  'Url': '/content/enforced/43233-81814b18-6ae4-4570-be9d-7459154a94b4_20231003_1202/LessonBuilder/lessonBuilder_2911898.html'},

    for itemid in placeholder_items:
        print(f"Updating HTML file for Lessons item {itemid}")

        updated = False

        # Get the HTML
        topic_path = f"{topic_prefix}lessonBuilder_{itemid}.html"
        topic_id = get_topic_id(content_toc, topic_path)
        if not topic_id:
            print(f"Topic for {topic_path} not found: possibly already updated")
            continue

        topic_url = f"{brightspace_url}/d2l/api/le/{API_VERSION}/{import_id}/content/topics/{topic_id}/file"

        print(f"Contents from: {topic_url}")
        page_html = get_lessons_html(topic_url, brightspace_session)

        # print(f"HTML:\n{page_html}")

        if not page_html:
            raise Exception(f"Could not get content page from {topic_url}")

        soup_html = BeautifulSoup(page_html, 'html.parser')

        if not soup_html:
            raise Exception("Cannot parse HTML from {topic_url}")

        updated = False

        # Institution specific
        org_ou=6606

        # Replace the placeholders with embed code
        placeholders = soup_html.find_all('p', attrs={"data-type": "placeholder"})
        for placeholder in placeholders:

            # print(f"placeholder: {placeholder.prettify()}")
            placeholder_name = placeholder['data-name']
            sakai_id_enc = placeholder['data-sakai-id']
            sakai_id = base64.b64decode(sakai_id_enc).decode("utf-8").replace(SITE_ID, transfer_id)

            file_display_name = get_content_displayname(f"{site_folder}{SITE_ID}-archive", sakai_id)

            media_id = get_media_id(content_toc, sakai_id, file_display_name)

            if media_id and topic_id:
                if placeholder['data-item-type'] == ItemType.RESOURCE:
                    # Link
                    link_html = f'<p><a href="/d2l/common/dialogs/quickLink/quickLink.d2l?ou={{orgUnitId}}&type=mediaLibrary&contentId={media_id}" target="_blank" rel="noopener">{placeholder_name}</a></p>'
                else:
                    # Embed
                    link_html = f'<p><iframe src="/d2l/wcs/mp/mediaplayer.d2l?ou={org_ou}&amp;entryId={media_id}&amp;captionsEdit=False" title="{placeholder_name}" width="700px" style="max-width: 100%; min-height: 340px; aspect-ratio: 700/393;" scrolling="no" frameborder="0" allowfullscreen="allowfullscreen" webkitallowfullscreen="true" mozallowfullscreen="true"></iframe></p>'

                placeholder.replace_with(BeautifulSoup(link_html, 'html.parser'))
                updated = True
            else:
                logging.warning(f"Ignoring {sakai_id} - possibly already run")
                # raise Exception(f"Could not get media_id or topic_id for {sakai_id}")

        # Replace links
        for link in soup_html.find_all('a'):

            if not link.get('href'):
                # Anchor tag, not a link
                continue

            # Link without any parameters
            href = link.get('href').split("?")[0]
            href = href.replace(f"{brightspace_url}{topic_prefix}", "")
            print(f"looking at: {link}")

            if href.startswith("../") and supported_media_type(APP, href):

                sakai_id = f'/group/{transfer_id}/{href[3:]}'
                file_display_name = get_content_displayname(f"{site_folder}{SITE_ID}-archive", sakai_id)
                media_id = get_media_id(content_toc, sakai_id, file_display_name)

                link_href = f"/d2l/common/dialogs/quickLink/quickLink.d2l?ou={{orgUnitId}}&type=mediaLibrary&contentId={media_id}"
                print(f"Updated link href to: {link_href}")
                link['href'] = link_href
                updated = True

        # Replace embedded audio (AMA-612)
        for link in soup_html.find_all(['audio', 'video']):
            print(f"got HTML5 audio/video: {link}")
            src = link.get('src')
            if not src:
                source = link.find('source')
                if source:
                    src = source.get('src')

            if src:
                src = src.replace(f"{brightspace_url}{topic_prefix}", "")

                if src.startswith("../"):
                    sakai_id = f'/group/{transfer_id}/{src[3:]}'
                    file_display_name = get_content_displayname(f"{site_folder}{SITE_ID}-archive", sakai_id)
                    media_id = get_media_id(content_toc, sakai_id, file_display_name)
                    print(f"replacing with HTML5 embed for {src}")

                    # Use an iframe embed
                    link_html = f'<p><iframe src="/d2l/wcs/mp/mediaplayer.d2l?ou={org_ou}&amp;entryId={media_id}&amp;captionsEdit=False" title="{file_display_name}" width="700px" style="max-width: 100%; min-height: 340px; aspect-ratio: 700/393;" scrolling="no" frameborder="0" allowfullscreen="allowfullscreen" webkitallowfullscreen="true" mozallowfullscreen="true"></iframe></p>'
                    link.replace_with(BeautifulSoup(link_html, 'html.parser'))
                    updated = True

        if updated:
            new_topic_filename = f"lessonBuilder_{itemid}a.html"
            update_endpoint = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['update_html_file'].format(import_id, topic_id))
            json_response = middleware_api(APP, update_endpoint, payload_data={'html': soup_html.html.encode("utf-8"), 'name': new_topic_filename}, method='PUT')
            if not 'status' in json_response or json_response['status'] != 'success':
                raise Exception(f"Error updating topic {topic_id}: {json_response}")
            logging.info(f"Updating topic {import_id} / {topic_id} for Lessons item {itemid}")

    # raise Exception("paused")

    return

def main():
    global APP
    parser = argparse.ArgumentParser(description="Check for placeholders in lessons and embed multimedia file",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("IMPORT_ID", help="The org unit id of the imported site")
    parser.add_argument("TRANSFER_ID", help="The site id as imported into Brightspace")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['IMPORT_ID'], args['TRANSFER_ID'])

if __name__ == '__main__':
    main()
