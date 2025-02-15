#! /usr/bin/python3

# Create Amathuba content page with lecture summaries from Opencast

import argparse
import os
import sys
import logging
import json
import copy
import markdown
import pytz
import tempfile

from datetime import datetime
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config

from lib.local_auth import getAuth
from lib.d2l import middleware_api, get_course_info, get_content_toc, create_lti_quicklink
from lib.opencast import Opencast

def setup_logging(APP, logger, log_file):

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(process)d %(filename)s(%(lineno)d) %(message)s')

    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # create stream handler (logging in the console)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    sh.setFormatter(formatter)
    logger.addHandler(sh)

def is_published(event):
    return 'publication_status' in event and "engage-player" in event['publication_status']

def has_captions(event):

    if 'publications' in event:
        for pub in event['publications']:
            if 'media' in pub:
                for media in pub['media']:
                    if media['mediatype'] == "text/vtt":
                        return True

    return False

def intro_embolden(section_txt, context, phrase):

    # Replace first occurrence only
    if section_txt.startswith(context):
        #print(f"BOLD")
        return section_txt.replace(phrase, f"**{phrase}**", 1)

    return section_txt

def txt_to_html(section_txt):

    #print(f"Section text:\n{section_txt}")

    # Section emphasis
    section_txt = intro_embolden(section_txt, "Here's a concise summary", "concise summary")
    section_txt = intro_embolden(section_txt, "Here are some practice questions based on the lecture transcript", "practice questions")
    section_txt = intro_embolden(section_txt, "Here are the key points, concepts, and definitions from the lecture transcript", "key points, concepts, and definitions")

    # Bullet points
    section_txt = section_txt.replace("\n   - ", "\n\t- ").replace("\n- ", "\n\t- ")

    return markdown.markdown(section_txt)

def get_first_module(content_toc, module_title):

    module_list = list(filter(lambda x: x['Title'] == module_title, content_toc['Modules']))

    if not module_list:
        return None

    # There could be multiple matches
    return module_list[0]

def get_first_topic(module, topic_title):

    topic_list = list(filter(lambda x: x['Title'] == topic_title, module['Topics']))

    if not topic_list:
        return None

    # There could be multiple matches
    return topic_list[0]

def update_topic(APP, org_id, module_id, topic_id, topic_html):

    update_endpoint = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['update_html_file'].format(org_id, topic_id))

    # We need to give this a unique name otherwise Brightspace will append "- Copy"
    suffix = datetime.today().strftime('%Y%m%d_%H:%M:%S')
    filename = f"lecture-summaries_{module_id}_{suffix}.html"

    logging.debug(f"Updating topic {topic_id} with new filename {filename}")

    json_response = middleware_api(APP, update_endpoint, payload_data={'html': topic_html, 'name' : filename }, method='PUT')
    if 'status' not in json_response or json_response['status'] != 'success':
        raise Exception(f"Error updating topic {topic_id}: {json_response}")

    return

def add_topic(APP, org_id, base_path, module_id, topic_name, topic_html):

    add_endpoint = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['add_topic_from_file'].format(org_id, module_id))
    #filename = f"summaries-{os.getpid()}.html"

    detail = json.dumps( { "Title": topic_name, "ShortTitle": topic_name, "IsHidden": True, "Url": f"{base_path}lecture-summaries_{module_id}.html" } )

    # Write the HTML to a temporary file
    with tempfile.NamedTemporaryFile(mode='w+t') as tmp_f:
        tmp_f.write(topic_html)
        tmp_f.seek(0)

        # print(f"URL: {add_endpoint}\ndetail: {detail}")

        json_response = middleware_api(APP, add_endpoint, files = {"file": tmp_f, "detail": (None, detail)}, method='POST')

        #print(f"Add topic: {json_response}")

        if 'data' in json_response and 'Id' in json_response['data']:
            return json_response['data']['Id']

    return None

def add_or_replace_topic(APP, series_id, org_id, course_info, module_name, topic_name, topic_html):

    content_toc = get_content_toc(APP, org_id)

    module = get_first_module(content_toc, module_name)

    if module is None:
        logging.warning(f"Skipping {org_id} - no module {module_name}")
        return False

    module_id = module['ModuleId']

    logging.info(f"Updating topic '{topic_name}' in {org_id} module id {module_id}")

    topic = get_first_topic(module, topic_name)
    topic_id = None

    if topic is None:
        # Create
        logging.debug(f"CREATE: {course_info}")
        base_path = course_info['Path']
        topic_id = add_topic(APP, org_id, base_path, module_id, topic_name, topic_html)
    else:
        # Replace
        logging.debug(f"REPLACE: {course_info}")
        topic_id = topic["TopicId"]
        update_topic(APP, org_id, module_id, topic_id, topic_html)

    # Get the TOC. If the topic doesn't exist, create it with new contents like this:
    #   POST /d2l/api/le/(version)/(orgUnitId)/content/modules/(moduleId)/structure/¶

    # If it does exist, update its contents like this:
    # PUT /d2l/api/le/(version)/(orgUnitId)/content/topics/(topicId)/file¶

    logging.info(f"Series {series_id} summaries: https://amathuba.uct.ac.za/d2l/le/lessons/{org_id}/topics/{topic_id}")

    return

def get_enriched_events(APP, oc_client, series_id):

    utc_zone = pytz.utc
    local_timezone =  pytz.timezone('Africa/Johannesburg')

    # Get events with publications
    events = oc_client.get_events(series_id)

    if events is None:
        logging.info(f"No events for series {series_id}")
        return []

    enriched_events = []
    published = 0
    captions = 0

    for event in events:

        eventId = event['identifier']

        # Start time in local timezone
        event_start = event['start']
        utc_start = datetime.strptime(event_start, "%Y-%m-%dT%H:%M:%SZ")
        utc_start = utc_zone.localize(utc_start)
        local_start = utc_start.astimezone(local_timezone)
        local_start_str = local_start.strftime("%-d %b %Y %-H:%M")

        event['local_start'] = local_start_str

        if is_published(event) and event['processing_state'] == "SUCCEEDED":

            # Published event
            published += 1

            if has_captions(event):

                captions += 1
                legacy_features = False

                if legacy_features:
                    # 2024 pilot - from 2025 these are in published json
                    # https://cilt.atlassian.net/browse/OPENCAST-3254
                    asset = oc_client.get_asset(eventId)

                    # Extract the URL containing "nibity"
                    attachments = asset['mediapackage']['attachments']['attachment']
                    for attachment in attachments:
                        if 'nibity' in attachment['@id']:
                            nibity_url = attachment['url']
                            json_from_zip = oc_client.get_asset_zip_contents(nibity_url, f"{eventId}.json")
                            if not json_from_zip:
                                logging.info(f"** {eventId} {local_start_str} attachment does not contain {eventId}.json")
                                continue

                            event_content = json.loads(json_from_zip)
                            nid = list(event_content.keys())[0]
                            event['enriched'] = event_content[nid]
                            enriched_events.append(event)
                else:
                    # Find attachmment with "flavor": "captions/json"
                    for pub in event['publications']:
                        if pub['channel'] == 'engage-player':
                            attachments = pub['attachments']
                            for attachment in attachments:
                                if attachment['flavor'] == "captions/json":
                                    features_url = attachment['url']
                                    logging.info(f"Series {series_id} has transcript summaries {features_url}")
                                    features_json = oc_client.get_published_attachment(features_url)
                                    event_content = json.loads(features_json)
                                    nid = list(event_content.keys())[0]
                                    event['enriched'] = event_content[nid]
                                    enriched_events.append(event)

                if 'enriched' in event:
                    logging.info(f"** {eventId} {local_start_str} is published with captions and summaries")
                else:
                    logging.info(f"** {eventId} {local_start_str} is published with captions but no summaries")

            else:
                logging.debug(f"** {eventId} {local_start_str} is published but has no captions")
        else:
            logging.debug(f"** {eventId} {local_start_str} is not published")

    logging.info(f"Series {series_id} has {len(events)} events, {published} published events, {captions} published with captions, {len(enriched_events)} with summaries")

    return enriched_events

def create_mp_quicklink(APP, event_id, title, org_id):

    ql_url = "{}{}{}".format(APP['opencast']['base_url'], APP['opencast']['content_item_path'], event_id)

    ql_data = [ {
        'Name' : 'tool',
        'Value' : f'/play/{event_id}'
    } ]

    #print(f"QL_URL: {ql_url}")
    #print(f"DATA: {ql_data}")

    lti_link_data = {
        # Get unique Url if LTI match and "play" tool link
        "Url" : ql_url,
        "Title" : title,
        "Description" : title,
        "CustomParameters": ql_data
    }

    # Create a new QuickLink - the "Url" is used as a unique value
    quicklink_url = create_lti_quicklink(APP, org_id, lti_link_data)

    #print(f"Got {quicklink_url} for payload: {lti_link_data}")

    return quicklink_url


def create_summaries(APP, oc_client, series_id, summary = True, update = False):

    # TODO change to transcript-features
    EXT_SERIES_TRANSCRIPT_ID = "transcription-type"
    EXT_SERIES_SITE_ID = "site-id"

    # Check the Amathuba site id from extended metadata
    series_metadata = oc_client.get_series_metadata(series_id, "ext/series")

    if series_metadata is None:
        logging.warning(f"Opencast series {series_id} not found or missing extended metadata")
        return

    org_id = None
    featurelist = None

    for m_item in series_metadata:

        # Get the LMS org unit id
        if m_item['id'] == EXT_SERIES_SITE_ID:
            org_id = m_item['value']

        # Get the transcription features which have been enabled (expect an array)
        if m_item['id'] == EXT_SERIES_TRANSCRIPT_ID:
            featurelist = m_item['value']

    ## TODO Testing
    featurelist = "transcription,summary"

    # Check for features enabled other than transcription
    if not featurelist or (len(featurelist) == 1 and 'transcript' in featurelist):
        logging.info(f"No transcription features selected for series {series_id}: {featurelist}")
        return

    logging.info(f"Enabled transcription features for series {series_id}: {featurelist}")

    # Nowhere to publish to
    if not org_id:
        return

    # Check valid course in Amathuba
    amathuba = False

    if len(org_id) <= 6:
        try:
            course_info = get_course_info(APP, org_id)
        except Exception:
            logging.warning("No Brightspace site found for org id {org_id} for series {series_id}")
            return

        logging.info(f"Series {series_id} is '{course_info['Name']}' https://amathuba.uct.ac.za/d2l/home/{org_id}")
        amathuba = True
    else:
        logging.info(f"Series {series_id} is https://vula.uct.ac.za/portal/site/{org_id}")

    if not amathuba:
        logging.info("Series {series_id} site ID {org_id} is not a Brightspace ID")
        return

    # Check for enriched events
    enriched_events = get_enriched_events(APP, oc_client, series_id)

    logging.info(f"Series {series_id} enriched events: {len(enriched_events)}")

    if len(enriched_events) == 0:
        return

    ### Summary page

    # Start with an empty template
    template = "lecture-summary"
    with open(f'{parent}/templates/{template}.html', 'r') as f:
        tmpl_contents = f.read()
    tmpl = BeautifulSoup(tmpl_contents, 'html.parser')

    accordion = tmpl.find("div", class_="accordion")
    if accordion is None:
        raise Exception("No Creator accordion found")

    card_index = 0
    card_template = accordion.find("div", class_="card")
    event_model = None

    for event in enriched_events:

        event_model = event['enriched']['summary']['model']

        eventId = event['identifier']
        card_item = copy.copy(card_template)

        summary_txt = event['enriched']['summary']['content'][0]['text']
        kp_txt = event['enriched']['key_points']['content'][0]['text']
        pq_txt = event['enriched']['practice_questions']['content'][0]['text']

        # Not doing anything with these at present
        # mcq_txt = event['enriched']['multiple_choice']['content'][0]['text']
        # fr_txt = event['enriched']['further_reading']['content'][0]['text']

        #print(f"MCQ: {mcq_txt}")
        #print(f"KP: {kp_txt}")
        #print(f"PQ: {pq_txt}")

        # Presenter list
        presenters = ', '.join(event['presenter'])
        event_title = f"{event['local_start']} {event['title']}"

        logging.debug(f"Adding {eventId} '{event_title}' to summary")

        # <h2 class="card-title" data-itemprop="0|0">Lecture 1 title</h2>
        # <div class="card-body" data-itemprop="0|1"><p>Lecture 1 summary</p></div>

        # Create an LTI quicklink for this event
        quicklink_url = create_mp_quicklink(APP, eventId, event_title, org_id)
        ql_markup = f'<p><a href="{quicklink_url}" target="_blank">Watch the video</a></p>'

        # Append a new card
        card_title  = card_item.find("h2", class_="card-title")
        card_title['data-itemprop']=f"{card_index}|0"
        card_title.string = event_title

        card_body = card_item.find("div", class_="card-body")
        card_body['data-itemprop']=f"{card_index}|1"

        # Presenter and watch link
        card_p = card_body.find("p")
        card_p.string = f"Presenter(s): {presenters}"
        card_body.append(BeautifulSoup(ql_markup, "html.parser"))

        # Summary items
        card_body.append(BeautifulSoup(txt_to_html(summary_txt), "html.parser"))
        card_body.append(BeautifulSoup(txt_to_html(kp_txt), "html.parser"))
        card_body.append(BeautifulSoup(txt_to_html(pq_txt), "html.parser"))

        accordion.append(card_item)
        card_index += 1

    if event_model:
        # Set the AI model label
        model_span = tmpl.find("span", id="oc-model-label")
        if model_span:
            model_span.string = event_model

    # Remove the template card and generate the new HTML
    card_template.decompose()
    new_html = str(tmpl)

    logging.info(f"Model: {event_model}")

    # Create or update the topic page
    if update:
        add_or_replace_topic(APP, series_id, org_id, course_info, "Lecture Videos", "Lecture Summaries", new_html)
    #else:
    #    print(f"New HTML:\n{new_html}")

    return

def main():

    APP = config.config.APP

    logfile = f"{parent}/log/oc-summaries.log"
    print(f"Logging to {logfile}")

    logger = logging.getLogger()
    setup_logging(APP, logger, logfile)

    parser = argparse.ArgumentParser(description="This script gets Brightspace import statuses",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--list", help="File containing a list of Opencast series IDs")
    parser.add_argument("--series", help="The Opencast series ID on which to work")

    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('--mcq', action='store_true')
    parser.add_argument('--update', action='store_true')
    args = vars(parser.parse_args())

    if args['debug']:
        logger.setLevel(logging.DEBUG)

    series_id = args['series']
    series_list = args['list']
    update = args['update'] or False

    ocAuth = getAuth('Opencast', ['username', 'password'])
    if ocAuth['valid']:
        oc_client = Opencast(APP['opencast']['base_url'], ocAuth['username'], ocAuth['password'])
    else:
        raise Exception('Opencast authentication required')

    if series_id:
        create_summaries(APP, oc_client, series_id, summary = True, update = update)

    if series_list:
        with open(series_list, "r") as list_file:
            for series_id in list_file:
                series_id = series_id.replace("\n","")
                create_summaries(APP, oc_client, series_id, summary = True, update = update)

    logging.info("Done")

if __name__ == '__main__':
    main()
