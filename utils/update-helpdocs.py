#! /usr/bin/python3

import json
import csv

helpdocs = {}

# Read helpdocs csv (key,url)
with open("helpdocs.csv", 'r', encoding='utf-8-sig') as data:
   for line in csv.reader(data):
       if line[0] in helpdocs and line[1] != helpdocs[line[0]]:
           print(f"duplicate helpdoc key {line[0]} with different URL")
       else:
           helpdocs[line[0]] = line[1]

print("Found {} help docs\n".format(len(helpdocs)))

# Iterating through the json list
with open('../config/conversion_issues.json', 'r') as f:

    data = json.load(f)

    # Issues
    for issue in data['issues']:
        key = issue['key']
        if key in helpdocs:
            # print("Found a helpdoc for {}: {}".format(key, helpdocs[key]))
            if 'info' in issue:
                if issue['info']['url'] != helpdocs[key]:
                    print(f"Updating info URL for issue {key}")
                    issue['info']['url'] = helpdocs[key]
            else:
                print(f"Adding info URL for issue {key}")
                issue['info'] = { "url" : helpdocs[key], "a" : "more info" }
        else:
            if issue['active']:
                print(f"Issue {key} has no associated help url")

    print("----")

    # Tools
    for issue in data['tools']:
        key = issue['key']
        toolkey = "tool:" + key
        if toolkey in helpdocs:
            # print("Found a helpdoc for {}: {}".format(key, helpdocs[key]))
            if 'info' in issue:
                if  issue['info']['url'] != helpdocs[toolkey]:
                    print(f"Updating info URL for tool {key} from {issue['info']['url']} to {helpdocs[toolkey]}")
                    issue['info']['url'] = helpdocs[toolkey]
            else:
                print(f"Adding info URL for tool {key}")
                issue['info'] = { "url" : helpdocs[toolkey], "a" : "more info" }
        else:
            if 'found' in issue:
                print(f"Tool {toolkey} has no associated help url")
            else:
                print(f"Tool {toolkey} has no associated found info or help url")

    
# Write out the file
with open('conversion_issues_new.json', 'w') as f:
        json.dump(data, f, indent=2, sort_keys=False)

