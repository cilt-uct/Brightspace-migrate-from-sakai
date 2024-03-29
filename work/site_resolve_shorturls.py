#!/usr/bin/python3

## This script resolves and updates all /x/ shortened URLs in all XML files
## REF: AMA-241

import sys
import os
import argparse
import re
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from config.logging_config import *
from lib.utils import resolve_redirect

def run(SITE_ID, APP):
    logging.info('Site: Resolving shortened URLs : {}'.format(SITE_ID))

    xml_folder = "{}{}-archive/".format(APP['archive_folder'], SITE_ID)
    qti_folder = "{}{}-archive/qti/".format(APP['archive_folder'], SITE_ID)

    archive_files = [entry for entry in os.scandir(xml_folder) if entry.name.endswith('.xml')]
    qti_files = [entry for entry in os.scandir(qti_folder) if entry.name.endswith('.xml')]

    xml_files = archive_files + qti_files

    shorturl_prefix = f"{APP['sakai_url']}/x/"

    # print(f"Resolving prefixes: {shorturl_prefix}")

    for file in xml_files:
        if APP['debug']:
            print(file.path)

        with open(f'{file.path}', 'r+', encoding='utf8') as f:
            # read and replace content
            content = f.read()

            if shorturl_prefix in content:
                print(f"Updating short URLs in {file.name}")
                # reset file cursor and write to file
                f.seek(0)
                f.write(replace_urls(shorturl_prefix, content))
                f.truncate()

    if APP['debug']:
        print("all done")

    return True

def replace_urls(shorturl_prefix, content):

    re_pattern = shorturl_prefix.replace("/","\\/") + "[A-Za-z]{6}"
    print(f"pattern: {re_pattern}")
    shorturls = re.findall(re_pattern, content)

    replacements = {}

    for url in shorturls:
        # print(f"Found shorturl: {url}")
        resolved_url = resolve_redirect(url)
        if resolved_url:
            replacements[url] = resolved_url

    # print(f"Replacements: {replacements}")

    for shorturl in replacements.keys():
        print(f"Replacing {shorturl} with {replacements[shorturl]}")
        content = content.replace(shorturl, replacements[shorturl])

    return content

def main():
    global APP
    parser = argparse.ArgumentParser(description="AMA-241 This script resolves shortened URLs",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
