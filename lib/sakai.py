# Methods that call Sakai webservices

import sys
import os
import requests
import logging
import zeep
import time

from requests import Session
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings
from datetime import timedelta

disable_warnings(InsecureRequestWarning)

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.local_auth import getAuth
from lib.utils import format_bytes

class SizeExceededError(Exception):
    pass

class SecurityError(Exception):
    pass

class Sakai:

    ## Validate connection to a Sakai server and store the server config
    def __init__(self, APP):
        self.base_url = APP['sakai_url']
        self.server_config = None
        self.debug = APP['debug']
        self.APP = APP

        try:
            # Unauthentication access
            config_url = f"{self.base_url}/direct/server-config.json"
            response = requests.get(config_url)

            if response.status_code != 200:
                raise Exception(f"Unable to connect to Sakai server at {self.base_url}")

            self.server_config = response.json()

            # Authentication access
            self.SAKAI = getAuth(APP['auth']['sakai'], ['username', 'password'])

            if not self.SAKAI['valid']:
                raise Exception("Authentication required")

            logging.debug(f"Connected to Sakai server at {self.base_url}")

        except Exception as e:
            logging.error(f"Unable to connect to Sakai instance at {self.base_url}: {e}")

    ## Get a server configuration value
    def config(self, config_name):

        if self.server_config:
            for cv in self.server_config['server-config_collection']:
                if cv['name'] == config_name:
                    return cv['value']

        return None

    def url(self):
        return self.base_url

    ## Get a site's title
    def get_site_title(self, SITE_ID):

        site_title = None

        session = Session()
        transport = zeep.Transport(session=session, timeout=60)

        # Zeep client for login and out
        login_client = zeep.Client(wsdl="{}/sakai-ws/soap/login?wsdl".format(self.SAKAI['url']), transport=transport)

        # Disable SSL cert validation (only if needed)
        login_client.transport.session.verify = False

        try:
            session_details = login_client.service.loginToServer(self.SAKAI['username'], self.SAKAI['password']).split(',')
            if self.debug:
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

            if self.debug:
                print(logout)

            return site_title

        except zeep.exceptions.Fault as fault:
            logging.error("Webservices error calling method on {} with username {}".format(self.SAKAI['url'], self.SAKAI['username']))
            raise Exception(fault)

    ## Archive a site
    def archive_site(self, SITE_ID):

        auth = self.SAKAI

        if SITE_ID.startswith("!"):
            raise SecurityError(f"Not archiving special sites: {SITE_ID}")

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
            if self.debug:
                print(session_details)

            # Check max permitted content size
            max_size = self.APP['export']['limit']

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
            archive_ws = self.APP['archive']['endpoint']
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

            if self.debug:
                print(logout)

            return succeeded

        except zeep.exceptions.Fault as fault:
            logging.error("Webservices error calling method on {} with username {}".format(auth['url'], auth['username']))
            raise Exception(fault)

    ## Archive site with retry
    def archive_site_retry(self, SITE_ID, max_tries=3):

        succeeded = False

        logging.debug("Archiving site {SITE_ID} retries {max_tries}")

        for i in range(max_tries):
            try:
               succeeded = self.archive_site(SITE_ID)
               break

            except SizeExceededError as se:
                logging.warning(se)
                # No point in retrying
                break

            except SecurityError as sec:
                raise Exception(sec)

            except Exception as e:
                logging.warning(f"Error archiving site {SITE_ID}: retry {i} of {max_tries}")
                if self.debug:
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

    ## Set one or more site properties
    def set_site_properties(self, SITE_ID, property_set):

        succeeded = True
        ALLOWED_PROPS = [ 'brightspace_conversion_success', 'brightspace_conversion_date', 'brightspace_conversion_status',
                'brightspace_imported_site_id', 'brightspace_course_site_id' ]

        try:

            session = Session()
            props_updated = 0

            # Zeep client for running site archive - timeout is 7200 sec = 2 hrs
            transport = zeep.Transport(session=session, timeout=7200)

            # Zeep client for login and out
            login_client = zeep.Client(wsdl="{}/sakai-ws/soap/login?wsdl".format(self.SAKAI['url']), transport=transport)
            login_client.transport.session.verify = False

            session_details = login_client.service.loginToServer(self.SAKAI['username'], self.SAKAI['password']).split(',')
            logging.debug(f'session_details {session_details}')

            sakai_client = zeep.Client(wsdl="{}/sakai-ws/soap/sakai?wsdl".format(session_details[1]), transport=transport)
            sakai_client.transport.session.verify = False

            for k in property_set:
                if k['name'] in ALLOWED_PROPS:
                    succeeded = sakai_client.service.setSiteProperty(session_details[0], SITE_ID, k['name'], k['value']) == "success"
                    if succeeded:
                        logging.info(f"Site {SITE_ID} property {k['name']}={k['value']}")
                        props_updated += 1
                else:
                    logging.warning(f"Ignoring property {k['name']}: not in allowed set of properties")

            # logout
            logout = login_client.service.logout(session_details[0])
            logging.debug(f'logout: {logout}')

            logging.info(f'Updated {props_updated} site_properties : {SITE_ID}')

            return (props_updated > 0)

        except zeep.exceptions.Fault as fault:
            logging.error("Webservices error calling method on {} with username {}".format(self.SAKAI['url'], self.SAKAI['username']))
            raise Exception(fault)

    ## Set a single site property
    def set_site_property(self, SITE_ID, property_name, property_value):

        return self.set_site_properties(SITE_ID, [{ 'name' : property_name, 'value' : property_value }])
