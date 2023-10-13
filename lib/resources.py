# Classes and functions for Resources

import lxml.etree as ET
import base64

# Return a set of resource IDs in the site
def get_resource_ids(xml_src):
    tree = ET.parse(xml_src)
    root = tree.getroot()
    ids = [x.get('id') for x in root.findall(".//resource")]
    return ids

# Get the userid and if available EID (username) of the user who owns this content ID
# 1. From content.xml, get resource with id=sakai_id
# - creator userid is base64-decode of <property name="CHEF:creator" value="...">
# 2. From user.xml, get user with id= owner id
# - creator eid is eid attribute
# 3. If the user is not found in user.xml (e.g. the user is not a member of the site, or
# the file is embedded from another site), return eid = None
def get_content_owner(site_folder, sakai_id):

    if sakai_id.startswith("/url/"):
        # Not a real Sakai ID - used in Lessons
        return (None, None)

    content_src = f'{site_folder}/content.xml'
    content_tree = ET.parse(content_src)
    content_root = content_tree.getroot()

    item = content_root.find(f".//resource[@id='{sakai_id}']")
    if item is None:
        raise Exception(f"Resource {sakai_id} not found in {content_src}")

    owner = item.find('./properties/property[@name="CHEF:creator"]')
    if owner is None:
        raise Exception(f"No creator property found for {sakai_id} in {content_src}")

    owner_userid_enc = owner.get('value')
    owner_userid = base64.b64decode(owner_userid_enc).decode("utf-8")

    user_src = f'{site_folder}/user.xml'
    user_tree = ET.parse(user_src)
    user_root = user_tree.getroot()

    user = user_root.find(f".//user[@id='{owner_userid}']")
    owner_eid = user.get('eid') if user is not None else None

    return (owner_userid, owner_eid)

def resource_exists(site_folder, sakai_id):

    if sakai_id.startswith("/url/"):
        # Not a real Sakai ID - used in Lessons
        return False

    content_src = f'{site_folder}/content.xml'
    content_tree = ET.parse(content_src)
    content_root = content_tree.getroot()

    if content_root.find(f".//resource[@id='{sakai_id}']") is not None:
        return True

    if content_root.find(f".//collection[@id='{sakai_id}']") is not None:
        return True

    return False

# Return display name for a content item, if available otherwise None
def get_content_displayname(site_folder, sakai_id):

    if sakai_id.startswith("/url/"):
        # Not a real Sakai ID - used in Lessons
        return None

    content_src = f'{site_folder}/content.xml'
    content_tree = ET.parse(content_src)
    content_root = content_tree.getroot()

    if sakai_id.endswith("/"):
        # Collection
        item = content_root.find(f".//collection[@id='{sakai_id}']")
    else:
        # Resource
        item = content_root.find(f".//resource[@id='{sakai_id}']")

    if item is None:
        raise Exception(f"Resource {sakai_id} not found in {content_src}")

    displayprop = item.find('./properties/property[@name="DAV:displayname"]')
    if displayprop is None:
        return None

    displayname = str(base64.b64decode(displayprop.get("value")).decode('utf-8'))
    return displayname
