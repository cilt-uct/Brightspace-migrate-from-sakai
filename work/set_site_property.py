#!/usr/bin/python3

## Workflow operation to update Sakai site property with migration status
## REF: AMA-254

import sys
import os
import argparse
import logging

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

import config.logging_config
import lib.sakai

def run(SITE_ID, APP, **kwargs):

    # Sakai webservices
    sakai_ws = lib.sakai.Sakai(APP)

    succeeded = False

    for k in kwargs:
        if sakai_ws.set_site_property(SITE_ID, k, kwargs[k]):
            logging.info(f"Site {SITE_ID} property {k}={kwargs[k]}")
            succeeded = True

    logging.info('Updated site_properties : {} {}'.format(SITE_ID, succeeded))

    return succeeded

def main():
    APP = config.config.APP
    parser = argparse.ArgumentParser(description="Workflow operation to update Sakai site property with migration status",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID on which to work")
    parser.add_argument('-d', '--debug', action='store_true')
    parser.add_argument("name", help="Property name")
    parser.add_argument("value", help="Property value")
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']
    if APP['debug']:
        config.logging_config.logger.setLevel(logging.DEBUG)

    new_kwargs = {'SITE_ID' : args['SITE_ID'], 'APP': APP, args['name'] : args['value']}
    run(**new_kwargs)

if __name__ == '__main__':
    main()
