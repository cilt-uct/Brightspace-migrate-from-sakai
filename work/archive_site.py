#!/usr/bin/python3

## This script will try and archive a Sakai site - this will create a ZIP file and return True if success
## REF:

import sys
import os
import argparse
import time
import zeep
import logging
from requests import Session
from datetime import timedelta
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

disable_warnings(InsecureRequestWarning)

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import format_bytes
from lib.local_auth import getAuth

class SizeExceededError(Exception):
    pass

def archive_site(SITE_ID, APP, auth):

    succeeded = False

    # Disable SSL cert validation (for srvubuclexxx direct URLs)
    session = Session()
    session.verify = False
    # Zeep client for running site archive - timeout is 7200 sec = 2 hrs
    transport = zeep.Transport(session=session, timeout=7200)

    # Zeep client for login and out
    login_client = zeep.Client(wsdl="{}/sakai-ws/soap/login?wsdl".format(auth['url']), transport=transport)
    login_client.transport.session.verify = False

    try:
        session_details = login_client.service.loginToServer(auth['username'], auth['password']).split(',')
        if (APP['debug']):
            print(session_details)

        # Check max permitted content size
        max_size = APP['export']['limit']

        sakai_content = zeep.Client(wsdl="{}/sakai-ws/soap/contenthosting?wsdl".format(session_details[1]), transport=transport)
        sakai_content.transport.session.verify = False

        logging.info("Checking Sakai site resources size for {} on server {}" .format(SITE_ID, session_details[1]))

        # Returns size in KB, -1 if invalid site id
        size_result = sakai_content.service.getSiteCollectionSize(session_details[0], SITE_ID)

        if int(size_result) >= 0:
            size_result = size_result * 1024
            if (size_result < max_size):
                logging.info(f"Resources size for {SITE_ID} is {format_bytes(size_result)}")
            else:
                logout = login_client.service.logout(session_details[0])
                raise SizeExceededError(f"Resources size in {SITE_ID} of {format_bytes(size_result)} exceeds limit {format_bytes(max_size)}")

        # Go ahead with archive
        archive_ws = APP['archive']['endpoint']
        sakai_client = zeep.Client(wsdl="{}/{}?wsdl".format(session_details[1], archive_ws), transport=transport)
        sakai_client.transport.session.verify = False

        logging.info("Archiving Sakai site {} on server {}" .format(SITE_ID, session_details[1]))

        start_time = time.time()
        archive_result = sakai_client.service.archiveSite(session_details[0], SITE_ID)

        if (archive_result == "success"):
            logging.info("Archive for site {} completed".format(SITE_ID))
            succeeded = True
        else:
            logging.error("Archive for site {} failed with result: {}".format(SITE_ID, archive_result))

        logging.info("\tElapsed time {}".format(str(timedelta(seconds=(time.time() - start_time)))))

        # logout
        logout = login_client.service.logout(session_details[0])

        if (APP['debug']):
            print(logout)

        return succeeded

    except zeep.exceptions.Fault as fault:
        logging.error("Webservices error calling method on {} with username {}".format(auth['url'], auth['username']))
        raise Exception(fault)

def archive_site_retry(SITE_ID, APP, max_tries=3):

    succeeded = False
    tmp = getAuth(APP['auth']['sakai_archive'])
    if (tmp is not None):
        SAKAI = {'url' : tmp[0], 'username' : tmp[1], 'password' : tmp[2]}
    else:
        logging.error("Authentication required")
        return succeeded

    if (APP['debug']):
        print(f'{SITE_ID}\n{APP}\n{SAKAI}')

    for i in range(max_tries):
        try:
           succeeded = archive_site(SITE_ID, APP, SAKAI)
           break

        except SizeExceededError as se:
            logging.warning(se)
            # No point in retrying
            break

        except Exception as e:
            logging.warning(f"Error archiving site {SITE_ID}: retry {i} of {max_tries}")
            if (APP['debug']):
                print(e)
                for remaining in range(60, 0, -1):
                    sys.stdout.write("\r")
                    sys.stdout.write("Attempt {} - retrying in {:2d} seconds".format(i, remaining))
                    sys.stdout.flush()
                    time.sleep(1)
                sys.stdout.write("\r")
            else:
                time.sleep(300)
            continue

    return succeeded

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script will try and archive a Sakai site - this will create a ZIP file and return True if success",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID for which to transfer fixed file")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    APP['debug'] = APP['debug'] or args['debug']

    archive_site_retry(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
