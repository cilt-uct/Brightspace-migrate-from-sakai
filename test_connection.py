#!/usr/bin/python3

## Checks that a call to Brightspace via the middleware (middleware_d2l_api) succeeds,
## by calling /d2l/api/lp/(version)/users/whoami

import sys
import json
import logging

import config.config
import config.logging_config

from lib.d2l import middleware_d2l_api


def main():
    APP = config.config.APP

    payload = {
        'url': f"{APP['brightspace_api']['lp_url']}/users/whoami",
        'method': 'GET',
    }
    print(f"Calling {payload['url']} via middleware {APP['middleware']['base_url']}")

    try:
        json_response = middleware_d2l_api(APP, payload_data=payload, retries=0)
    except Exception as e:
        logging.exception(e)
        print(f"FAILED: {e}")
        return 1

    if json_response and json_response.get('status') == 'success':
        print("SUCCESS")
        print(json.dumps(json_response.get('data'), indent=2))
        return 0

    print(f"FAILED: {json_response}")
    return 1


if __name__ == '__main__':
    sys.exit(main())
