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
from datetime import datetime
from bs4 import BeautifulSoup

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.config

from lib.local_auth import getAuth
from lib.d2l import middleware_d2l_api, get_course_info, get_toc
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
            if 'attachments' in pub:
                for attach in pub['attachments']:
                    if attach['mediatype'] == "text/vtt":
                        return True

    return False

def create_summaries(APP, series_id):

    utc_zone = pytz.utc
    local_timezone =  pytz.timezone('Africa/Johannesburg')

    ocAuth = getAuth('Opencast', ['username', 'password'])
    if ocAuth['valid']:
        oc_client = Opencast(APP['opencast']['base_url'], ocAuth['username'], ocAuth['password'])
    else:
        raise Exception('Opencast authentication required')

    # Check the Amathuba site id from extended metadata
    series_metadata = oc_client.get_series_metadata(series_id, "ext/series")
    for m_item in series_metadata:
        if m_item['id'] == "site-id":
            org_id = m_item['value']

    # Check valid course
    course_info = get_course_info(APP, org_id)
    logging.info(f"Generating summary page for {org_id} '{course_info['Name']}'")

    events = oc_client.get_events(series_id)
    if events is None:
        print(f"No events for series {series_id}")
        return None

    # Start with an empty template
    template = "lecture-summary"
    with open(f'{parent}/templates/{template}.html', 'r') as f:
        tmpl_contents = f.read()
    tmpl = BeautifulSoup(tmpl_contents, 'html.parser')

    accordion = tmpl.find("div", class_="accordion")
    if accordion is None:
        raise Exception("No Creator accordion found")

    card_template = accordion.find("div", class_="card")

    card_index = 0

    for event in events:

        if is_published(event) and has_captions(event):

            # Published event
            eventId = event['identifier']
            #print(f"Published event with captions: {eventId} {event['start']} {event}")

            # Get this from published json in due course
            # https://jira.cilt.uct.ac.za/browse/OPENCAST-3254
            asset = oc_client.get_asset(eventId)

            # Extract the URL containing "nibity"
            attachments = asset['mediapackage']['attachments']['attachment']
            for attachment in attachments:
                if 'nibity' in attachment['@id']:
                    nibity_url = attachment['url']
                    # print("URL of the nibity file:", nibity_url)
                    event_content = json.loads(oc_client.get_asset_zip_contents(nibity_url, f"{eventId}.json"))

                    nid = list(event_content.keys())[0]

                    event_model = event_content[nid]['summary']['model']
                    summary = event_content[nid]['summary']['content'][0]['text']

                    # print(f"Model {event_model} summary:\n{summary}")

                    event['enriched'] = event_content[nid]

            if 'enriched' in event:
                card_item = copy.copy(card_template)

                summary_txt = event['enriched']['summary']['content'][0]['text']

                # Preesnter list
                presenters = ', '.join(event['presenter'])

                # Start time in local timezone
                event_start = event['start']
                utc_start = datetime.strptime(event_start, "%Y-%m-%dT%H:%M:%SZ")
                utc_start = utc_zone.localize(utc_start)
                local_start = utc_start.astimezone(local_timezone)
                local_start_str = local_start.strftime("%-d %b %Y %-H:%M")

                # Format with markdown
                summary_txt = summary_txt.replace("\n   - ", "\n\t- ").replace("\n- ", "\n\t- ")
                summary_html = markdown.markdown(summary_txt)

                event_title = f"{local_start_str} {event['title']}"

                print(f"{eventId} {event_title}")

                # <h2 class="card-title" data-itemprop="0|0">Lecture 1 title</h2>
                # <div class="card-body" data-itemprop="0|1"><p>Lecture 1 summary</p></div>

                # Append a new card
                card_p = card_item.find("p")
                card_p.string = f"Presenter(s): {presenters}"

                card_title  = card_item.find("h2", class_="card-title")
                card_title['data-itemprop']=f"{card_index}|0"
                card_title.string = event_title

                card_body = card_item.find("div", class_="card-body")
                card_body['data-itemprop']=f"{card_index}|1"
                card_body.append(BeautifulSoup(summary_html, "html.parser"))

                accordion.append(card_item)
                card_index += 1

    # Remove the template card and generate the new HTML
    card_template.decompose()
    new_html = str(tmpl)

    print(new_html)

    # Now update the site

    # Login to fetch files directly
    #WEB_AUTH = getAuth('BrightspaceWeb', ['username', 'password'])
    #if not WEB_AUTH['valid']:
    #    raise Exception('Web Authentication required [BrightspaceWeb]')

    #brightspace_url = APP['brightspace_url']

    #login_url = f"{brightspace_url}/d2l/lp/auth/login/login.d2l"
    #brightspace_session = web_login(login_url, WEB_AUTH['username'], WEB_AUTH['password'])

    # Get the ToC
    # content_toc = json.loads(get_toc(APP, import_id, brightspace_session))

    # print(f"New html:\n{new_html}")

    return

def main():

    APP = config.config.APP

    logger = logging.getLogger()
    setup_logging(APP, logger, "summaries.log")

    parser = argparse.ArgumentParser(description="This script gets Brightspace import statuses",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("SERIES_ID", help="The Opencast series on which to work")

    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    if args['debug']:
        logger.setLevel(logging.DEBUG)

    create_summaries(APP, args['SERIES_ID'])

    logging.info("Done")

if __name__ == '__main__':
    main()
