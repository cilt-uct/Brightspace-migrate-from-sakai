#!/usr/bin/python3

## This script will upload files from the webdav folder to the server for the Site and Spesified Folder
## REF: AMA-30

import sys
import os
import re
import json
import csv
import base64
import argparse
import xml.etree.ElementTree as ET

from tqdm import tqdm
from webdav3.client import Client

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *
from lib.local_auth import *

def viewBar(a,b):
    # original version
    res = a/int(b)*100
    sys.stdout.write('\rComplete precent: %.2f %%' % (res))
    sys.stdout.flush()

def tqdmWrapViewBar(*args, **kwargs):
    try:
        from tqdm import tqdm
    except ImportError:
        # tqdm not installed - construct and return dummy/basic versions
        class Foo():
            @classmethod
            def close(*c):
                pass
        return viewBar, Foo
    else:
        pbar = tqdm(*args, **kwargs)  # make a progressbar
        last = [0]  # last known iteration, start at 0
        def viewBar2(a, b):
            pbar.total = int(b)
            pbar.update(int(a - last[0]))  # update pbar with increment
            last[0] = a  # update last known iteration
        return viewBar2, pbar  # return callback, tqdmInstance

def get_size(filename):
    if not os.path.exists(filename):
        return None

    return os.path.getsize(filename)

def Func_CallBack():
    print("File Length : ")

def process_webdav(SITE_ID, target_folder):
    logging.info('Webdav: upload {}'.format(SITE_ID))

    webdav_folder = r'{}{}-webdav/'.format(APP['archive_folder'], SITE_ID)
    create_folders(webdav_folder)

    # print(f'{webdav_folder}\n{target_folder}')

    xml_src = r'{}/content.xml'.format(webdav_folder)
    remove_unwanted_characters(xml_src)

    tree = ET.parse(xml_src)
    root = tree.getroot()

    tmp = getAuth('BrightspaceWebdav')
    if (tmp is not None):
        WEBDAV = {'webdav_hostname' : tmp[0], 'webdav_login': tmp[1], 'webdav_password' : tmp[2]}
    else:
        logging.error("Authentication required")
        return 0

    # print(WEBDAV)

    webdav = Client(WEBDAV)
    if webdav:
        webdav_files = webdav.list(target_folder)

        # print(json.dumps(webdav_files, indent=4))

        if root.tag == 'archive':
            for resource in root.findall(".//resource"):
                name_tag = resource.find('.//property[@name="DAV:displayname"]')
                name = str(base64.b64decode(name_tag.attrib['value']))

                try:
                    remote_file = r'{}/{}'.format(target_folder, resource.attrib['rel-id'])
                    local_file = r'{}/{}'.format(webdav_folder, resource.attrib['body-location'])

                    # see if the file we want to upload exists
                    if os.path.exists(local_file):
                        # print('{} {} {} {} {} {}'.format(resource.tag,
                        #                 resource.attrib['body-location'],
                        #                 format_bytes(int(resource.attrib['content-length'])),
                        #                 resource.attrib['content-type'],
                        #                 name,
                        #                 resource.attrib['rel-id']))

                        # Checking existence of the resource we want to replace
                        if webdav.check(remote_file):
                            before_upload = webdav.info(remote_file)
                            local_size = os.path.getsize(local_file)

                            # if the file size is the same - assume it is there and continue to next file
                            if (local_size != int(before_upload['size'])):
                                logging.info('Uploading {} -> {} : {}'.format(format_bytes(int(local_size)),
                                                                        format_bytes(int(before_upload['size'])),
                                                                        resource.attrib['rel-id']))

                                # cbk, pbar = tqdmWrapViewBar(ascii=True, unit='b', unit_scale=True)
                                webdav.upload_sync( remote_path=remote_file, local_path=local_file) #, progress=cbk)
                                # pbar.close()

                                after_upload = webdav.info(remote_file)
                                logging.info('     Done {}'.format(format_bytes(int(after_upload['size']))))
                            else:
                                logging.info('Same file {} == {} : {}'.format(format_bytes(int(local_size)),
                                                                        format_bytes(int(before_upload['size'])),
                                                                        resource.attrib['rel-id']))
                        else:
                            logging.error("{} remote file does not exist.".format(resource.attrib['rel-id']))
                except Exception as e:
                    logging.error("{} processing failed for file {}".format(resource.attrib['rel-id'], e))

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script will upload files from the webdav folder to the server for the Site and Spesified Folder",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("FOLDER", help="The Folder to upload to")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    process_webdav(args['SITE_ID'], args['FOLDER'])

if __name__ == '__main__':
    main()
