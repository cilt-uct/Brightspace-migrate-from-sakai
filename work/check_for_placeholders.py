import argparse
import os
import sys
import pprint

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *

# Get an HTML page directly from Brightspace
def get_lessons_html(url, session):

    print(f"Getting HTML from {url}")
    r = session.get(url, timeout=30)
    return r.text

# Get the media ID for a given audio or video path
# Match the filename in the Structure of the unit with the given parent id,
# and then find the video URL in topics
def get_media_id(unit_pages, topics, parent_id, filename):

    print(f"Checking for parent_id {parent_id} with filename {filename}")

    unit_list = list(filter(lambda x: x['Id'] == parent_id, unit_pages))
    if unit_list:
        unit = unit_list[0]
    else:
        print(f"No unit!")
        return None

    print(f"Got unit: {unit}")

    for file in unit['Structure']:
        if filename == file['Title']:
            topic_id = file['Id']
            print("Got topic of the video: {topic_id}")

            topic = list(filter(lambda x: x['Id'] == topic_id, topics))[0]
            media_url = topic['Url']

            print(f"Got URL: {media_url}")
            media_id = media_url.split(':')[-1].split('/')[0]

            return media_id

    return None

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
            html = BeautifulSoup(item.attrs['html'], 'html.parser')
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

    # Get all unit pages. A Lessons page in Sakai is a unit in Brightspace
    endpoint = "{}{}{}".format(APP['middleware']['base_url'], APP['middleware']['content_root_url'], import_id)
    response = middleware_api(APP, endpoint)
    unit_pages = response['data']

    print("### UNIT PAGES ###")
    #pprint.pprint(unit_pages)

    # Get all content topics
    # The URL for a topic HTML file is named with the Lessons item id.
    # Item ID 2911898:
    #  'Url': '/content/enforced/43233-81814b18-6ae4-4570-be9d-7459154a94b4_20231003_1202/LessonBuilder/lessonBuilder_2911898.html'},

    topic_endpoint = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['get_topics'].format(import_id))
    topics_response = middleware_api(APP, topic_endpoint)
    topics = topics_response['data']

    print("\n\n### TOPICS ###")
    #pprint.pprint(topics)

    for itemid in placeholder_items:
        print(f"Updating HTML file for Lessons item {itemid}")

        updated = False

        # Get the topic ID with URL that matches
        topic = list(filter(lambda x: x['Url'].endswith(f"/LessonBuilder/lessonBuilder_{itemid}.html"), topics))

        if not topic:
            print(f"WARN no topic found for {itemid}")
            continue

        print(f"Found matching topic: {topic[0]}")
        topic_url = "{}{}".format(brightspace_url, topic[0]['Url'])
        topic_id = topic[0]['Id']
        parent_id = topic[0]['ParentModuleId']
        print(f"URL: {topic_url} parent_id {parent_id}")

        # Get the HTML
        page_html = get_lessons_html(topic_url, brightspace_session)

        # print(f"Got HTML: {page_html}")

        soup_html = BeautifulSoup(page_html, 'html.parser')
        placeholders = soup_html.find_all('p', attrs={"data-type": "placeholder"})
        updated = False

        # Replace the placeholders with embed code
        for placeholder in placeholders:
            file_name = placeholder.attrs['data-name']
            sakai_id = placeholder.attrs['data-sakaiid']
            print(f"Got placeholder: {file_name} {sakai_id}")

            # Institution specific
            org_ou=6606

            media_id = get_media_id(unit_pages, topics, parent_id, file_name)

            if media_id:
                link = BeautifulSoup(f'<p><iframe src="/d2l/wcs/mp/mediaplayer.d2l?ou={org_ou}&amp;entryId={media_id}&amp;captionsEdit=False" title="{file_name}" width="700px" style="max-width: 100%; min-height: 340px; aspect-ratio: 700/393;" scrolling="no" frameborder="0" allowfullscreen="allowfullscreen" webkitallowfullscreen="true" mozallowfullscreen="true"></iframe></p>', 'html.parser')
                placeholder.replace_with(link)
                updated = True

        if updated:
            update_endpoint = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['update_html_file'].format(import_id, topic_id))
            middleware_api(APP, update_endpoint, payload_data={'html': str(soup_html)}, method='PUT')


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
