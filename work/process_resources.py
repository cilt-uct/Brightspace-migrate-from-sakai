#!/usr/bin/python3

## This script will check the resources in the site and move the larger ones as defined in
## placeholder.csv with placeholder files and move the originals to a webdav folder 
## to be uploaded with upload_with_webdav.py later
## REF: AMA-30

import sys
import os
import re
import json
import csv
import base64
import argparse
import xml.etree.ElementTree as ET

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import *

def move_to_webdav(src_folder, dest_folder, tmp_file, filename):

    file_src = r'{}{}'.format(src_folder, filename)
    file_src_size = get_size(file_src)
    file_tmp = r'{}/placeholders/{}'.format(parent, tmp_file)
    file_tmp_size = get_size(file_tmp)
    file_target = r'{}{}'.format(dest_folder, filename)
    file_target_size = get_size(file_target)

    # print(f'{file_src}\n{file_tmp}\n{file_target}')

    if file_tmp_size is None:
        return False

    # print('copying: {}'.format(shutil.copyfile(file_src, file_target)))

    # print('src: {}'.format(get_size(file_src)))
    # print('tmp: {}'.format(get_size(file_tmp)))
    # print('target: {}'.format(get_size(file_target)))

    # we have a file to replace the file with
    if file_target_size:
        # ok so there is a file ...
        logging.debug('exist - src: {} to {}'.format(get_size(file_src), get_size(file_target)))

        if file_src_size <= file_target_size:
            # target and source is same size - so tmp needs to replace src
            shutil.copyfile(file_tmp, file_src)
    else:
        #normal operation all is fine
        shutil.copyfile(file_src, file_target)
        shutil.copyfile(file_tmp, file_src) 
        
    return True

def run(SITE_ID, APP):
    logging.info('Content : {}'.format(SITE_ID))

    src_folder  = r'{}{}-archive/'.format(APP['archive_folder'], SITE_ID)
    dest_folder = r'{}{}-webdav/'.format(APP['archive_folder'], SITE_ID)

    # print(f'{src_folder}\n{dest_folder}')

    create_folders(src_folder)
    create_folders(dest_folder)

    xml_src = r'{}/content.xml'.format(src_folder)
    xml_old = r'{}/content.old'.format(src_folder)
    shutil.copyfile(xml_src, xml_old)
    shutil.copyfile(xml_src, '{}/content.xml'.format(dest_folder))   
    
    remove_unwanted_characters(xml_src)

    placeholder_default = []
    with open(f'{parent}/placeholder_default.csv', mode='r') as data:
        for row in csv.DictReader(data):
            placeholder_default.append(row)
    if (len(placeholder_default) > 0):
        placeholder_default = placeholder_default[0]
    else:
        placeholder_default = {'Size': '5242880', 'File': 'tmp.zip'}

    placeholders = []
    with open(f'{parent}/placeholders.csv', mode='r') as data:
        for row in csv.DictReader(data):
            placeholders.append(row)

    infile = open(xml_src,"r")
    contents = infile.read()
    soup = BeautifulSoup(contents, 'xml')

    root = ET.fromstring(str(soup))

    if root.tag == 'archive':
        for resource in root.findall(".//resource"):
            name = resource.find('.//property[@name="DAV:displayname"]')

            try:
                file_type = next(row for row in placeholders if row["Type"] == resource.attrib['content-type'])
                local_size = os.path.getsize(r'{}/placeholders/{}'.format(parent, file_type['File']))

                # we don't replace the site information file
                if (base64.b64decode(name.attrib['value']).decode('ascii') != 'Site Information'):
                    print('{} {} {} {} {}'.format(resource.tag, 
                                    resource.attrib['body-location'], 
                                    format_bytes(int(resource.attrib['content-length'])), 
                                    resource.attrib['content-type'], 
                                    base64.b64decode(name.attrib['value']).decode('ascii')))
                    # try with
                    # if (int(file_type['Size']) <= int(resource.attrib['content-length'])):

                    # minimum size 
                    if (int(local_size) < int(resource.attrib['content-length'])):
                        
                        # met the threshold we move the file to webadv
                        if move_to_webdav(src_folder, dest_folder, file_type['File'], resource.attrib['body-location']):
                            logging.debug("Replacing with {}".format(file_type['File']))
                        else:
                            logging.error("ERR replacing file {}".format(resource.attrib['body-location']))
            except:
                # not processing this file - we don't have the type for it.
                if (int(placeholder_default['Size']) <= int(resource.attrib['content-length'])):
                    if move_to_webdav(src_folder, dest_folder, placeholder_default['File'], resource.attrib['body-location']):
                        logging.debug("Replacing file with tmp.zip because it's larger than 20971520")
                    else:
                        logging.debug("{} Not replacing this file.".format(str(base64.b64decode(name.attrib['value']))))   

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script will check the resources in the site and move the larger ones as defined in\n" +
                                                " placeholder.csv with placeholder files and move the originals to a webdav folder\n" +
                                                " to be uploaded with upload_with_webdav.py later.",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())
    
    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
