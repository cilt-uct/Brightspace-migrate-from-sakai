#! /usr/bin/python3

# Push a CSV into an Explorance Blue data source
# https://cilt.atlassian.net/browse/AMA-1092
# Temporary home before this is moved into middleware

import os
import sys
import logging
import argparse

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.local_auth import getAuth
from lib.explorance import PushDataSource
import config.logging_config

def main():

    parser = argparse.ArgumentParser(description="Update an Explorance Blue Data Source from a CSV file",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--id')
    parser.add_argument('--name')
    parser.add_argument('--csv')
    parser.add_argument('--dev', action='store_true')
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument('-l', '--list', action='store_true')
    parser.add_argument('-b', '--blocks', action='store_true')
    args = vars(parser.parse_args())

    if args['debug']:
        config.logging_config.logger.setLevel(logging.DEBUG)

    blue_source = "BlueTest" if args['dev'] else "Blue"
    blue_api = getAuth(blue_source, ['apikey', 'url'])

    if not blue_api['valid']:
        raise Exception("Missing configuration")

    logging.info(f"Explorance endpoint {blue_api['url']}")
    PDS = PushDataSource(blue_api['url'], blue_api['apikey'])

    # List datasources
    if args['list']:
        ds_list = PDS.getDataSourceList()
        print(f"Datasources:\n{ds_list}")

        if args['blocks']:
            for ds in ds_list:
                ds_id = ds['SourceID']
                ds_name = ds['Caption']
                print(f"Datasource id {ds_id}")

                db_list = PDS.getDataBlockInformation(ds_id)
                print(f"Datasource \'{ds_name}\' id {ds_id} data blocks:\n{db_list}")

            print("Done blocks.")

        return

    # Push a CSV file to a datasource
    # (Live Data9 = Courses Instructors)
    # (Test Data25 = Courses Instructors)

    csv_file = args['csv']
    ds_id = args['id']
    ds_name = args['name']

    # Get data source id by name
    if not ds_id and ds_name:
        ds_id = PDS.getDataSourceId(ds_name)

    if not csv_file or not ds_id:
        logging.error("Must specify both CSV and ID")
        exit(1)

    if not os.path.exists(csv_file):
        logging.error(f"CSV file {csv_file} not found")
        exit(1)

    PDS.PushCSV(ds_id, csv_file)

if __name__ == '__main__':
    main()
