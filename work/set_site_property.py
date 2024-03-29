#!/usr/bin/python3

## Workflow operation to update Sakai site property with migration status
## REF: AMA-254

import sys
import os
import argparse
import zeep

from requests import Session

from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

disable_warnings(InsecureRequestWarning)

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *

VALID = ['brightspace_conversion_success', 'brightspace_conversion_date', 'brightspace_conversion_status', 'brightspace_imported_site_id']

def run(SITE_ID, APP, **kwargs):
    succeeded = True

    try:
        tmp = getAuth(APP['auth']['sakai'])
        if (tmp is not None):
            auth = {'url' : tmp[0], 'username' : tmp[1], 'password' : tmp[2]}
        else:
            raise Exception("Authentication required")

        # Disable SSL cert validation (for srvubuclexxx direct URLs)
        session = Session()
        session.verify = False

        # Zeep client for running site archive - timeout is 7200 sec = 2 hrs
        transport = zeep.Transport(session=session, timeout=7200)

        # Zeep client for login and out
        login_client = zeep.Client(wsdl="{}/sakai-ws/soap/login?wsdl".format(auth['url']), transport=transport)
        login_client.transport.session.verify = False

        session_details = login_client.service.loginToServer(auth['username'], auth['password']).split(',')
        logging.debug(f'session_details {session_details}')

        sakai_client = zeep.Client(wsdl="{}/sakai-ws/soap/sakai?wsdl".format(session_details[1]), transport=transport)
        sakai_client.transport.session.verify = False

        for k in kwargs:
            logging.debug(f'{k} : {kwargs[k]} : {k in VALID}')

            if k in VALID:
                succeeded = sakai_client.service.setSiteProperty(session_details[0], SITE_ID, k, kwargs[k]) == "success"

        # logout
        logout = login_client.service.logout(session_details[0])
        logging.debug(f'logout: {logout}')

        logging.info('Updated site_properties : {} {}'.format(SITE_ID, succeeded))
        return succeeded

    except zeep.exceptions.Fault as fault:
        logging.error("Webservices error calling method on {} with username {}".format(auth['url'], auth['username']))
        raise Exception(fault)

def main():
    global APP
    parser = argparse.ArgumentParser(description="Workflow operation to update Sakai site property with migration status",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
