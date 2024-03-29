#!/usr/bin/python3
from __future__ import division

## This script transfers the 'fixed' zip file for a site to the sftp folder

import sys
import re
import os
import glob
import argparse
import time
import pymysql
import logging

from pymysql.cursors import DictCursor
from datetime import timedelta
import paramiko

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

def rename_to_final_destination(client, old_name, new_name):
    try:
        client.rename(old_name, new_name)
    except IOError as io:
        # IOError – if newpath is a folder, or something else goes wrong
        raise Exception(f"Failed to rename: {old_name}") from io

def set_uploaded_at(db_config, link_id, site_id):
    try:
        connection = pymysql.connect(**db_config, cursorclass=DictCursor)
        with connection:
            with connection.cursor() as cursor:
                # Create a new record
                sql = """UPDATE `migration_site` SET modified_at = NOW(), modified_by = 1, uploaded_at = NOW()
                         WHERE `link_id` = %s and site_id = %s;"""
                cursor.execute(sql, (link_id, site_id))

            connection.commit()

    except Exception:
        logging.error(f"Could not update migration record {link_id} : {site_id}")
        return None

def run(SITE_ID, APP, link_id = None, now_st = None, zip_file = None):

    src = None

    if zip_file:
        if os.path.exists(zip_file):
            src = zip_file
        else:
            raise Exception(f"File {src} does not exist")

    if not src:
        logging.debug(f"looking for file in output for {SITE_ID} with now_st '{now_st}' and {zip_file}")
        if now_st is None:
            now_st = ""
        for py in glob.glob('{}/*{}_fixed*{}.zip'.format(APP['output'], SITE_ID, now_st)):
            src = py

    if not src or not os.path.exists(src):
        raise Exception(f"No file to transfer for {SITE_ID}")

    # Check size here, although large zip files are failed in the create_zip action in the previous workflow
    filesize = get_size(src)
    maxsize = APP['ftp']['limit']

    if (filesize > maxsize):
        raise Exception("Zipped site {} is too large for D2L import: {} > {}".format(SITE_ID, format_bytes(filesize), format_bytes(maxsize)))

    logging.info(f'Uploading {src} {format_bytes(filesize)}')

    start_time = time.time()

    dest = r'{}/{}'.format(APP['ftp']['inbox'], os.path.basename(src))
    tmp_dest = re.sub('(zip)$', 'tmp', dest)

    tmp = getAuth('BrightspaceFTP')
    if (tmp is not None):
        SFTP = {'host' : tmp[0], 'username': tmp[1], 'password' : tmp[2]}
    else:
        raise Exception("SFTP Authentication required")

    tmp = getAuth(APP['auth']['db'])
    if (tmp is not None):
        DB_AUTH = {'host' : tmp[0], 'database': tmp[1], 'user': tmp[2], 'password' : tmp[3]}
    else:
        raise Exception("DB Authentication required")

    # Open the connection
    t = paramiko.Transport((SFTP['host'], 22))
    if APP['ftp']['log']:
        logging.getLogger("paramiko").setLevel(logging.DEBUG) # for example
        paramiko.util.log_to_file(f"{APP['ftp']['log_output']}/{SITE_ID}_ftp.log", level = "DEBUG")

    try:
        t.connect(username=SFTP['username'], password=SFTP['password'])

        if APP['ftp']['show_progress']:
            sftp = paramiko.SFTPClient.from_transport(t)
            sftp.get_channel().settimeout(300)
            cbk, pbar = tqdmWrapViewBar(ascii=True, unit='b', unit_scale=True)
            sftp.put(src, tmp_dest, callback=cbk)
            pbar.close()
        else:
            sftp = paramiko.SFTPClient.from_transport(t)
            sftp.get_channel().settimeout(300)
            sftp.put(src, tmp_dest)

        rename_to_final_destination(t.open_sftp_client(), tmp_dest, dest)
        t.close()

        if int(link_id) > 0:
            set_uploaded_at(DB_AUTH, link_id, SITE_ID)

    except Exception as e:
        raise Exception(f"Error while uploading {src}: {e}")

    logging.info("\t{}".format(str(timedelta(seconds=(time.time() - start_time)))))

def main():
    global APP
    parser = argparse.ArgumentParser(description="This script transfers a zip file for a site to the sftp folder",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID for which to transfer fixed file")
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-p', '--progress', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']
    APP['ftp']['show_progress'] = args['progress']

    run(args['SITE_ID'], APP, args)

if __name__ == '__main__':
    main()
