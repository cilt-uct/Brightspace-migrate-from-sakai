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

# See https://docs.valence.desire2learn.com/res/content.html

# Get an HTML page directly from Brightspace
def get_lessons_html(url, session):
    r = session.get(url, timeout=30)
    return r.text if r.status_code == 200 else None

# Returns ToC as JSON: https://docs.valence.desire2learn.com/res/content.html#get--d2l-api-le-(version)-(orgUnitId)-content-toc
def get_toc(base_url, org_id, session):
    api_url = f"{base_url}/d2l/api/le/1.67/{org_id}/content/toc"
    print(f"TOC from: {api_url}")
    r = session.get(api_url, timeout=30)
    return r.text if r.status_code == 200 else None

# Get the media ID for a given audio or video path
# Match the filename in the Structure of the unit with the given parent id,
# and then find the video URL in topics
def get_media_id(content_toc, topic_path, sakai_id):

    resource_node = list(filter(lambda x: x['Title'] == 'Resources', content_toc['Modules']))[0]
    toplevel_lessons = list(filter(lambda x: x['Title'] not in ('Resources','External Resources'), content_toc['Modules']))
    #print("LESSONS:\n")
    #pprint.pprint(toplevel_lessons)

    # /group/42190a5a-3b44-4eda-9fb9-83773b4f6410/
    media_paths = sakai_id.split('/')[3:]
    print(f"paths: {media_paths}")

    filename = media_paths[-1]

    media_id = None
    topic_id = None
    media_url = None

    # Find the media_id. First try to match on title in Lessons, if it's unique in the site.
    jpe_cs = f"$..Topics[?(@.Title='{filename}')]"
    jpe_files = parse(jpe_cs)
    topics = jpe_files.find(toplevel_lessons)

    topic_match = list(filter(lambda x: x.value['TypeIdentifier'] == 'ContentService', topics))

    if not topic_match:
        raise Exception(f"No match for mediapath '{sakai_id}' and Title = '{filename}' in Topics")

    media_url = None

    if len(topic_match)==1:
        print(f"Unique match for {filename}")
        media_url = topic_match[0].value['Url']
    else:
        # Find it another way
        print(f"Multiple matches: traversing path {sakai_id}")

        # The Sakai path contained in the id may not match the
        # Resources tree directly, because of display names and/or changes to folder
        # names made by the Brightspace importer.
        for path in media_paths:
            if path == filename:
                # We're at the end, so look for an activity
                topic = list(filter(lambda x: x['TypeIdentifier'] == 'ContentService' and x['Title'] == filename, resource_node['Topics']))[0]
                media_url = topic['Url']
                media_id = media_url.split(':')[-1].split('/')[0]
                break
            else:
                module_search = list(filter(lambda x: x['Title'] == path, resource_node['Modules']))

                if module_search:
                    resource_node = module[0]
                else:
                    raise Exception(f"Path element {path} from {sakai_id} not found in ToC")

    if not media_url:
        raise Exception("Cannot find media url for {filename}")

    # Audio or video content service media Url
    media_id = media_url.split(':')[-1].split('/')[0]

    print(f"media_id is: {media_id} from {media_url}")

    # Find the topic ID by matching on the URL for the underlying html file which is
    # named from the Sakai Lessons ID by the Brightspace import code. So this is
    # guaranteed to match immediately after the import.

    jpe = f"$..Topics[?(@.Url=='{topic_path}')]"
    jsonpath_expression = parse(jpe)
    topic_matches = jsonpath_expression.find(toplevel_lessons)

    if not topic_matches:
        # pprint.pprint(toplevel_lessons, indent=3)
        # raise Exception(f"No topic found with URL matching {topic_path}")
        # TODO
        return (None, None)

    for match in topic_matches:
        topic_id = match.value['TopicId']

    return (topic_id, media_id)


def run(SITE_ID, APP, import_id):

    logging.info('Replace placeholders with multimedia links for import_id: {}'.format(import_id))

    # Check that there are placeholders in this site
    site_folder = APP['archive_folder']
    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(site_folder, SITE_ID)
    remove_unwanted_characters(xml_src)
    file_path = os.path.join(site_folder, xml_src)

    placeholder_items = []
    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        items = soup.find_all('item', attrs={"type": "5"})
        for item in items:
            html = BeautifulSoup(item['html'], 'html.parser')
            if html.find('p', attrs={"data-type": "placeholder"}):
                placeholder_items.append(item['id'])

    # TODO check for inline HTML links to video and audio that need replacing (not placeholders)

    if placeholder_items:
        print(f"Placeholders in these item ids: {placeholder_items}")
    else:
        logging.info("No placeholders in Lessons content")
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

    #  'Url': '/content/enforced/43233-81814b18-6ae4-4570-be9d-7459154a94b4_20231003_1202/LessonBuilder/lessonBuilder_2911898.html'},

    for itemid in placeholder_items:
        print(f"Updating HTML file for Lessons item {itemid}")

        updated = False

        # Get the HTML
        topic_path = f"{content_defaultpath}LessonBuilder/lessonBuilder_{itemid}.html"
        topic_url = f"{brightspace_url}{topic_path}"

        print(f"Contents from: {topic_url}")
        page_html = get_lessons_html(topic_url, brightspace_session)

        if not page_html:
            raise Exception(f"Could not get content page from {topic_url}")

        soup_html = BeautifulSoup(page_html, 'html.parser')
        placeholders = soup_html.find_all('p', attrs={"data-type": "placeholder"})
        updated = False

        print(f"Item: {item.prettify()}")

        # Replace the placeholders with embed code
        for placeholder in placeholders:
            print(f"placeholder: {placeholder.prettify()}")
            placeholder_name = placeholder['data-name']
            sakai_id_enc = placeholder['data-sakai-id']
            sakai_id = base64.b64decode(sakai_id_enc).decode("utf-8")

            # Institution specific
            org_ou=6606

            (topic_id, media_id) = get_media_id(content_toc, topic_path, sakai_id)

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
                logging.warn(f"Ignoring {sakai_id} - possibly already run")
                # raise Exception(f"Could not get media_id or topic_id for {sakai_id}")

        if updated:
            update_endpoint = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['update_html_file'].format(import_id, topic_id))
            json_response = middleware_api(APP, update_endpoint, payload_data={'html': soup_html.html.encode("utf-8")}, method='PUT')
            print(f"Updating response: {json_response}")
            logging.info(f"Updating Amathuba topic {import_id} / {topic_id} for Lessons item {itemid}")

    return

def main():
    global APP
    parser = argparse.ArgumentParser(description="Check for placeholders in lessons and embed multimedia file",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("IMPORT_ID", help="The org unit id of the imported site")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP, args['IMPORT_ID'])

if __name__ == '__main__':
    main()
