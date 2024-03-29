#!/usr/bin/python3

## This script get the Sakai site title
## REF: AMA-447

import sys
import os
import argparse
import zeep
import logging

from requests import Session
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

disable_warnings(InsecureRequestWarning)

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.local_auth import getAuth

class SizeExceededError(Exception):
    pass

def get_site_title(SITE_ID, APP):

    site_title = None

    tmp = getAuth(APP['auth']['sakai'])
    if (tmp is not None):
        SAKAI = {'url' : tmp[0], 'username' : tmp[1], 'password' : tmp[2]}
    else:
        logging.error("Authentication required")
        return False

    # Disable SSL cert validation (for srvubuclexxx direct URLs)
    session = Session()
    session.verify = False
    transport = zeep.Transport(session=session, timeout=60)

    # Zeep client for login and out
    login_client = zeep.Client(wsdl="{}/sakai-ws/soap/login?wsdl".format(SAKAI['url']), transport=transport)
    login_client.transport.session.verify = False

    try:
        session_details = login_client.service.loginToServer(SAKAI['username'], SAKAI['password']).split(',')
        if (APP['debug']):
            print(session_details)

        sakai_client = zeep.Client(wsdl="{}/sakai-ws/soap/sakai?wsdl".format(session_details[1]), transport=transport)
        sakai_client.transport.session.verify = False

        logging.debug("Getting Sakai site title for {} on server {}" .format(SITE_ID, session_details[1]))

        title_result = sakai_client.service.getSiteTitle(session_details[0], SITE_ID)

        if title_result and not title_result.startswith("org.sakaiproject.exception.IdUnusedException"):
            logging.debug("Title for site {} is {}".format(SITE_ID, title_result))
            site_title = title_result
        else:
            # Not fatal, so we'll just warn
            logging.warning("Site {} title request failed with result: {}".format(SITE_ID, title_result))

        # logout
        logout = login_client.service.logout(session_details[0])

        if (APP['debug']):
            print(logout)

        return site_title

    except zeep.exceptions.Fault as fault:
        logging.error("Webservices error calling method on {} with username {}".format(SAKAI['url'], SAKAI['username']))
        raise Exception(fault)

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script will try and archive a Sakai site - this will create a ZIP file and return True if success",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID for which to transfer fixed file")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    site_title = get_site_title(args['SITE_ID'], APP)
    print(f"Site title: {site_title}")

if __name__ == '__main__':
    main()
