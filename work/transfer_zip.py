#!/usr/bin/python3
from __future__ import division

## This script transfers the 'fixed' zip file for a site to the sftp folder

import sys
import re
import os
import glob
import argparse
import time
import logging

from datetime import timedelta
import paramiko

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
import lib.db
from lib.utils import format_bytes, get_size
from lib.local_auth import getAuth

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

    SFTP = getAuth('BrightspaceFTP', ['hostname', 'username', 'password'])
    if not SFTP['valid']:
        raise Exception("SFTP Authentication required")

    mdb = lib.db.MigrationDb(APP)

    ssh_client = paramiko.SSHClient()
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())
    logging.getLogger("paramiko").setLevel(logging.WARNING)

    if APP['ftp']['log']:
        logging.getLogger("paramiko").setLevel(logging.DEBUG) # for example
        paramiko.util.log_to_file(f"{APP['log_folder']}/{SITE_ID}_ftp.log", level = "DEBUG")

    try:
        ssh_client.connect(SFTP['hostname'], 22, SFTP['username'], SFTP['password'], timeout=60)
        sftp = ssh_client.open_sftp()
        sftp.get_channel().settimeout(300)

        if APP['ftp']['show_progress']:
            cbk, pbar = tqdmWrapViewBar(ascii=True, unit='b', unit_scale=True)
            sftp.put(src, tmp_dest, callback=cbk)
            pbar.close()
        else:
            sftp.put(src, tmp_dest)

        rename_to_final_destination(sftp, tmp_dest, dest)

        if link_id and int(link_id) > 0:
            mdb.set_uploaded_at(link_id, SITE_ID)

    except Exception as e:
        raise Exception(f"Error while uploading {src}: {e}")

    finally:
        if ssh_client:
            ssh_client.close()

    logging.info("\t{}".format(str(timedelta(seconds=(time.time() - start_time)))))

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="This script transfers a zip file for a site to the sftp folder",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID for which to transfer fixed file")
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-p', '--progress', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']
    APP['ftp']['show_progress'] = args['progress']

    run(args['SITE_ID'], APP)

if __name__ == '__main__':
    main()
