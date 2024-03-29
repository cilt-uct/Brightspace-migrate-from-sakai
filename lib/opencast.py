# Opencast API support
# See also https://github.com/cilt-uct/Brightspace-Middleware/blob/main/d2l/services/web/project/opencast/opencast.py

import sys
import os
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.utils import *

def opencast_update_acls(APP, urls, import_id, target_site_id):

    if len(urls) == 0:
        return

    # Handle URLs of the form
    # https://media.uct.ac.za/lti/player/968e3f4e-f624-4506-a463-7f7729481381

    logging.info(f"Updating Opencast ACLs for sites {import_id},{target_site_id} for {len(urls)} items")

    return
