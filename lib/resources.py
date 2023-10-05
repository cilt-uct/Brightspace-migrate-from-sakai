# Classes and functions for Resources

import xml.etree.ElementTree as ET

# Return a set of resource IDs in the site
def get_resource_ids(xml_src):
    tree = ET.parse(xml_src)
    root = tree.getroot()
    ids = [x.get('id') for x in root.findall(".//resource")]
    return ids
