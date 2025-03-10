import argparse
import os
import sys
import json
import base64
import logging
from jsonpath_ng.ext import parse
from html import escape
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
from lib.utils import remove_unwanted_characters
from lib.local_auth import getAuth
from lib.lessons import get_archive_lti_link, ItemType, supported_media_type
from lib.resources import resource_exists, get_content_displayname
from lib.d2l import middleware_api, create_lti_quicklink, web_login, get_toc, get_instance_org_id, lti_available, get_lti_tool_providers

# See https://docs.valence.desire2learn.com/res/content.html

# Get an HTML page directly from Brightspace
def get_lessons_html(url, session):
    r = session.get(url, timeout=30)

    # Set the encoding explicitly
    r.encoding="UTF-8"

    return r.text if r.status_code == 200 else None

# Get the media ID for a given audio or video path
# Match the filename in the Structure of the unit with the given parent id,
# and then find the video URL in topics
def get_media_id(content_toc, file_path, displayname):

    print(f"get_media_id for {file_path} with displayname: {displayname}")

    resource_node = list(filter(lambda x: x['Title'] == 'Resources', content_toc['Modules']))[0]
    toplevel_lessons = list(filter(lambda x: x['Title'] not in ('Resources','External Resources'), content_toc['Modules']))

    media_paths = []

    # Sakai ID: /group/42190a5a-3b44-4eda-9fb9-83773b4f6410/
    if not file_path.startswith("/group/"):
        raise Exception(f"Unexpected path: {file_path}")

    media_paths = file_path.split('/')[3:]
    print(f"paths: {media_paths}")

    filename = media_paths[-1]

    # Search for filename in the Lessons tree
    print(f"Filename: {filename} Displayname: {displayname}")

    media_id = None
    media_url = None

    # Find the media_id. First try to match on title in Lessons, if it's unique in the site.
    filename_esc = filename.replace('"','\\"')
    jpe_cs = f'$..Topics[?(@.Title="{filename_esc}")]'
    jpe_lessons = parse(jpe_cs)

    topics = jpe_lessons.find(toplevel_lessons)

    topic_match = list(filter(lambda x: x.value['TypeIdentifier'] == 'ContentService', topics))

    if len(topic_match)==1:
        print(f"Unique match for {filename}")
        media_url = topic_match[0].value['Url']
    else:

        # See if the name is unique in the Resources tree
        search_name = filename
        if displayname:
            search_name = displayname
            if '.' not in search_name and '.' in filename:
                # append the original extension to match the Brightspace import behaviour
                file_ext = filename.split('.')[-1]
                search_name += f".{file_ext}"

            # Replace some special characters to match Brightspace mapping behaviour from displayname to topic name
            # e.g. "abc / xyz" > "abc _ xyz"
            search_name = search_name.replace('/','_')


        # Maximum length of a page title is 150 characters (not bytes)
        # c/f https://community.d2l.com/brightspace/kb/articles/18831-character-limitations-within-brightspace
        search_name_esc = search_name[0:150].replace('"','\\"')

        print(f"Searching for unique match for: {search_name_esc}")
        jpe_cs = f'$..Topics[?(@.Title="{search_name_esc}")]'
        jpe_resources = parse(jpe_cs)
        topics = jpe_resources.find(resource_node)
        topic_match = list(filter(lambda x: x.value['TypeIdentifier'] == 'ContentService', topics))

        if len(topic_match)==1:
            print(f"Unique match for {filename}")
            media_url = topic_match[0].value['Url']
        else:
            print(f"No unique match: number of results={len(topic_match)}")
            # Find it another way
            if topic_match:
                print(f"Multiple matches: traversing path {file_path}")
            else:
                print(f"No match in Lessons modules: looking in Resources for {file_path}")

            # The Sakai path contained in the id may not match the Resources tree directly,
            # because of display names and/or changes to folder names made by the Brightspace importer.
            for path in media_paths:
                if path == filename:
                    # We're at the end, so look for an activity matching the name
                    print(f"Searching for '{search_name}' within the topic")

                    topic_match = list(filter(lambda x: x['TypeIdentifier'] == 'ContentService' and x['Title'] == search_name, resource_node['Topics']))
                    if topic_match:
                        media_url = topic_match[0]['Url']
                        media_id = media_url.split(':')[-1].split('/')[0]
                        break
                    else:
                        raise Exception(f"No Activity found for '{filename}' searching for match with '{search_name}' at path '{path}'")
                else:
                    # TODO use the folder display name
                    module_search = list(filter(lambda x: x['Title'] == path, resource_node['Modules']))

                    if module_search and len(module_search) == 1:
                        print(f"Moving down to {path}")
                        resource_node = module_search[0]
                        continue

                    # Is it unique at this level?
                    print(f"Checking uniqueness for last time, no match or multiple matches for '{path}'")
                    topics = jpe_resources.find(resource_node)
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

    jpe = f'$..Topics[?(@.Url=="{topic_path}")]'
    jsonpath_expression = parse(jpe)
    topic_matches = jsonpath_expression.find(toplevel_lessons)

    if not topic_matches:
        # pprint.pprint(toplevel_lessons, indent=3)
        # raise Exception(f"No topic found with URL matching {topic_path}")

        # Expected where this script is run multiple times and no topics are using this underlying file directly
        return None

    # There could be multiple matches
    for match in topic_matches:
        topic_id = match.value['TopicId']

    return topic_id

# take {'tool': '/play/[MPID]'} > [{'Name':'tool', 'Value':'/play/[MPID]'}]
def dict_to_name_value_array(input_dict):
    return [{'Name': key, 'Value': value} for key, value in input_dict.items()]

# take "tool=/play/[MPID]" > [{'Name':'tool', 'Value':'/play/[MPID]'}]
def construct_CustomParameters(input_string):
    result = []
    lines = input_string.strip().splitlines()
    seen_keys = set()  # To track keys and prevent duplicates

    for line in lines:
        key, value = line.split('=', 1)
        if key not in seen_keys and value:  # Skip if the key is duplicate or value is empty/None
            result.append({'Name': key, 'Value': value})
            seen_keys.add(key)

    return result

# If the base_url for the LTI tool is a "[opencast]/lti" link and it refers to a "play" tool
# then return unique URL with the [domain][content_item_path][event_id] - which will play correctly
def get_quicklink_url(cfg, base_url, parms):
    if base_url not in cfg['lti']['match']:
        return base_url

    for entry in parms:
        if entry['Name'] == 'tool' and entry['Value'].startswith('/play/'):
            event_id = entry['Value'].split('/play/', 1)[1]
            return f"{cfg['lti']['match'][base_url]['url']}{event_id}"

    return base_url

def filter_name_value_array(cfg, base_url, parms):
    if base_url in cfg['lti']['match']:
        if not cfg['lti']['match'][base_url]['valid']:
            return parms
        return [entry for entry in parms if entry['Name'] in cfg['lti']['match'][base_url]['valid']]

    return parms

def run(SITE_ID, APP, import_id, transfer_id):

    logging.info(f'Replace placeholders with multimedia links for site {SITE_ID} import_id: {import_id}')

    # Check that there are placeholders in this site

    archive_path = f"{APP['archive_folder']}/{SITE_ID}-archive"
    lessons_src = f"{archive_path}/lessonbuilder.xml"
    remove_unwanted_characters(lessons_src)

    # Find the Lessons items that contain placeholders and/or audio/video links

    placeholder_items = []

    lti_content = False

    with open(lessons_src, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        items = soup.find_all('item', attrs={"type": "5"})
        for item in items:
            html = BeautifulSoup(item['html'], 'html.parser')

            # At least one placeholder
            if html.find('p', attrs={"data-type": "placeholder"}):
                placeholder_items.append(item['id'])
                continue

            # At least one LTI content item
            if html.find('p', attrs={"data-type": "lti-content"}):
                placeholder_items.append(item['id'])
                lti_content = True
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

    lti1x_providers = None
    lti1x_launches = None

    # Check the available LTI 1.x legacy tool providers
    if lti_content:
        lti1x_providers = get_lti_tool_providers(APP, import_id)
        lti1x_launches = [ x['LaunchPoint'] for x in lti1x_providers ]
        logging.info(f"Available LTI 1.x tool providers in {import_id}: {lti1x_launches}")

    # Login to fetch files directly
    WEB_AUTH = getAuth('BrightspaceWeb', ['username', 'password'])
    if not WEB_AUTH['valid']:
        raise Exception('Web Authentication required [BrightspaceWeb]')

    brightspace_url = APP['brightspace_url']

    login_url = f"{brightspace_url}/d2l/lp/auth/login/login.d2l"
    brightspace_session = web_login(login_url, WEB_AUTH['username'], WEB_AUTH['password'])

    # Get the ToC
    content_toc = json.loads(get_toc(APP, import_id, brightspace_session))
    print("#### TOC ####")

    #pprint.pprint(content_toc, width=sys.maxsize)
    #print(json.dumps(content_toc, indent=3))

    content_defaultpath = content_toc['Modules'][0]['DefaultPath']
    topic_prefix = f"{content_defaultpath}LessonBuilder/"

    #  'Url': '/content/enforced/43233-81814b18-6ae4-4570-be9d-7459154a94b4_20231003_1202/LessonBuilder/lessonBuilder_2911898.html'},

    # Institution org id
    org_ou = get_instance_org_id(APP)

    for itemid in placeholder_items:
        print(f"Updating HTML file for Lessons item {itemid}")

        updated = False

        # Get the HTML
        topic_path = f"{topic_prefix}lessonBuilder_{itemid}.html"
        topic_id = get_topic_id(content_toc, topic_path)
        if not topic_id:
            print(f"Topic for {topic_path} not found: possibly already updated")
            continue

        topic_url = f"{APP['brightspace_api']['le_url']}/{import_id}/content/topics/{topic_id}/file"

        print(f"Contents from: {topic_url}")
        page_html = get_lessons_html(topic_url, brightspace_session)

        # print(f"HTML:\n{page_html}")

        if not page_html:
            raise Exception(f"Could not get content page from {topic_url}")

        soup_html = BeautifulSoup(page_html, 'html.parser')

        if not soup_html:
            raise Exception("Cannot parse HTML from {topic_url}")

        updated = False

        # Replace the placeholders with embed code
        placeholders = soup_html.find_all('p', attrs={"data-type": "placeholder"})
        lti_links = soup_html.find_all('p', attrs={"data-type": "lti-content"})

        for placeholder in (placeholders + lti_links):

            # print(f"placeholder: {placeholder.prettify()}")
            placeholder_name = placeholder['data-name']
            placeholder_type = placeholder['data-type']
            sakai_id_enc = placeholder['data-sakai-id']
            sakai_id = base64.b64decode(sakai_id_enc).decode("utf-8").replace(SITE_ID, transfer_id)

            # Content links (audio, video)
            if placeholder_type == "placeholder":

                if not resource_exists(archive_path, sakai_id):
                    # Should always exist because we created a placeholder for it
                    raise Exception(f"Placeholder id '{sakai_id}' in Lessons item {itemid} not found in site resources")

                file_display_name = get_content_displayname(archive_path, sakai_id)
                media_id = get_media_id(content_toc, sakai_id, file_display_name)

                if media_id and topic_id:
                    if placeholder['data-item-type'] == ItemType.RESOURCE:
                        # Link
                        link_html = f'<p><a href="/d2l/common/dialogs/quickLink/quickLink.d2l?ou={{orgUnitId}}&type=mediaLibrary&contentId={media_id}" target="_blank" rel="noopener">{placeholder_name}</a></p>'
                    else:
                        # Embed
                        link_html = f'<p><iframe src="/d2l/wcs/mp/mediaplayer.d2l?ou={org_ou}&amp;entryId={media_id}&amp;captionsEdit=False" title="{placeholder_name}" width="700px" style="max-width: 100%; min-height: 340px;" scrolling="no" frameborder="0" allowfullscreen="allowfullscreen" webkitallowfullscreen="true" mozallowfullscreen="true"></iframe></p>'

                    placeholder.replace_with(BeautifulSoup(link_html, 'html.parser'))
                    updated = True
                else:
                    logging.warning(f"Ignoring {sakai_id} - possibly already run")
                    # raise Exception(f"Could not get media_id or topic_id for {sakai_id}")

            # Content links (audio, video)
            if placeholder_type == "lti-content":

                launch_url = None

                if sakai_id.startswith("/blti/"):
                    lti_id = sakai_id.replace("/blti/", "")
                    sakai_link_data = get_archive_lti_link(archive_path, lti_id)
                    if 'launch' in sakai_link_data:
                        launch_url = sakai_link_data['launch']

                if not sakai_link_data:
                    logging.warning(f"LTI placeholder: {sakai_id} '{placeholder_name}' unknown target")

                if sakai_link_data and not launch_url:
                    # TODO add support for migrating these (e.g. padlet)
                    logging.warning(f"LTI placeholder: {sakai_id} '{placeholder_name}' unsupported tool embedding")

                if sakai_link_data and launch_url:
                    logging.info(f"LTI placeholder: {sakai_id} '{placeholder_name}' {launch_url}")

                    # TODO Support LTI Advantage targets
                    if not lti_available(launch_url, lti1x_providers):
                        logging.warning(f"- skipping Quicklink creation for {launch_url}: no matching tool provider found")
                        continue

                    # Create a new quicklink in the target site
                    content_item = sakai_link_data['contentitem']
                    tool = None

                    if content_item:
                        # use the content item json object
                        # if it contains LTI tool custom parameter configurations
                        #     then construct a "Name", "Value" dictionary object as required by D2L
                        content_json = json.loads(content_item)
                        if '@graph' in content_json and len(content_json['@graph']) > 0:
                            ci_0 = content_json['@graph'][0]
                            if 'custom' in ci_0:
                                tool = dict_to_name_value_array(ci_0['custom'])
                        else:
                            if 'custom' in content_json:
                                tool = dict_to_name_value_array(content_json['custom'])

                    # Construct LTI custom parameter from the sakai link data
                    # return a "Name", "Value" dictionary object required by:
                    #     https://docs.valence.desire2learn.com/res/lti.html#LTI.CreateLtiLinkData
                    if tool is None:
                        tool = construct_CustomParameters(sakai_link_data['custom'])

                    # Assign None if the array is empty
                    if not tool:
                        tool = None

                    lti_link_data = {
                            # Get unique Url if LTI match and "play" tool link
                            "Url" : get_quicklink_url(APP, sakai_link_data['launch'], tool),
                            "Title" : sakai_link_data['title'],
                            "Description" : sakai_link_data['description'],
                            # filter unwanted parameters if LTI match
                            "CustomParameters": filter_name_value_array(APP, sakai_link_data['launch'], tool)
                    }

                    # Create a new QuickLink - the "Url" is used as a unique value
                    # if the Url exists - don't create a new link
                    # - in this case the unique Url is constructed with "set_quicklink_url"
                    quicklink_url = create_lti_quicklink(APP, import_id, lti_link_data)
                    logging.info(f"Quicklink for {lti_link_data['Url']} is {quicklink_url}")

                    if quicklink_url:

                        display = placeholder["data-display"]
                        title = sakai_link_data['title']

                        if display == "inline":
                            # embed
                            link_html = f'<p><iframe src="{quicklink_url}" allowfullscreen="allowfullscreen" allow="microphone *; camera *; autoplay *">{escape(title)}</iframe></p>'
                        else:
                            # link
                            link_html = f'<p><a href="{quicklink_url}" target="_self">{escape(title)}</a></p>'

                        placeholder.replace_with(BeautifulSoup(link_html, 'html.parser'))
                        updated = True

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

                # Check that it exists and isn't a broken link
                if not resource_exists(archive_path, sakai_id):
                    # TODO replace with a MISSING placeholder
                    print(f"Link target resource '{sakai_id}' does not exist")
                    continue

                file_display_name = get_content_displayname(archive_path, sakai_id)
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

                    if not resource_exists(archive_path, sakai_id):
                        # TODO replace with a Missing placeholder
                        print(f"Link target resource '{sakai_id}' does not exist")
                        continue

                    file_display_name = get_content_displayname(archive_path, sakai_id)
                    media_id = get_media_id(content_toc, sakai_id, file_display_name)
                    print(f"replacing with HTML5 embed for {src}")

                    # Use an iframe embed
                    link_html = f'<p><iframe src="/d2l/wcs/mp/mediaplayer.d2l?ou={org_ou}&amp;entryId={media_id}&amp;captionsEdit=False" title="{file_display_name}" width="700px" style="max-width: 100%; min-height: 340px;" scrolling="no" frameborder="0" allowfullscreen="allowfullscreen" webkitallowfullscreen="true" mozallowfullscreen="true"></iframe></p>'
                    link.replace_with(BeautifulSoup(link_html, 'html.parser'))
                    updated = True

        if updated:
            # TODO update only the underlying file, to handle the case where there are multiple topics using the same file
            # AMA-904 / AMA-910
            new_topic_filename = f"lessonBuilder_{itemid}a.html"
            update_endpoint = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['update_html_file'].format(import_id, topic_id))
            json_response = middleware_api(APP, update_endpoint, payload_data={'html': str(soup_html.html), 'name': new_topic_filename}, method='PUT')
            if 'status' not in json_response or json_response['status'] != 'success':
                raise Exception(f"Error updating topic {topic_id}: {json_response}")
            logging.info(f"Updating topic {import_id} / {topic_id} for Lessons item {itemid}")

    # raise Exception("paused")

    return

def main():
    APP = config.config.APP
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
