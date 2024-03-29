#! /usr/bin/python3

import json

# Iterating through the json list
with open('../config/conversion_issues.json', 'r') as f:

    data = json.load(f)

    print("Issues: {} Tools: {}\n".format(len(data['issues']), len(data['tools'])))

    print("==== active issues ====")
    for i in data['issues']:
        if i['active']:
            print("Key: {} Tool: {}".format(i['key'], i['tool']))

    print("\n==== tools ====")
    for i in data['tools']:
        print("key: {} Tool: {}".format(i['key'], i['name']))
