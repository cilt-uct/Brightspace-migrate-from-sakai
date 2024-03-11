# Classes and functions for Resources

import os
import lxml.etree as ET
import copy
import base64

# Return a set of resource IDs in the site
def get_resource_ids(xml_src):
    if os.path.exists(xml_src):
        tree = ET.parse(xml_src)
        root = tree.getroot()
        ids = [x.get('id') for x in root.findall(".//resource")]
        return ids
    else:
        return []

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

# Add a property subnode
def add_prop(props, prop_name, prop_val):

    prop_item = ET.Element("property")
    prop_item.set('enc', 'BASE64')
    prop_item.set('name', prop_name)
    prop_item.set('value', base64.b64encode(prop_val.encode('utf-8')))
    props.append(prop_item)

    return

# Move from attachment.xml to content.xml
def move_attachments(SITE_ID, site_folder, collection, move_list):

    content_src = f'{site_folder}/content.xml'
    content_tree = ET.parse(content_src)
    content_root = content_tree.getroot()

    attach_src = f'{site_folder}/attachment.xml'
    attach_tree = ET.parse(attach_src)
    attach_root = attach_tree.getroot()

    content_container = content_root.find("org.sakaiproject.content.api.ContentHostingService")
    attach_container = attach_root.find("org.sakaiproject.content.api.ContentHostingService")

    collection_id = f"/group/{SITE_ID}/{collection}/"

    rewrite = False

    if content_root.find(f".//collection[@id='{collection_id}']") is not None:
        print(f"Got collection {collection}")
    else:
        # Create the target collection under <org.sakaiproject.content.api.ContentHostingService>
        print(f"CREATE collection {collection_id}")

        collection_el = ET.Element("collection")
        collection_el.set('id', collection_id)
        collection_el.set('rel-id', collection)
        collection_el.set('resource-type', 'org.sakaiproject.content.types.folder')
        #collection_el.set('sakai:access_mode', 'inherited')
        #collection_el.set('sakai:hidden', 'false')

        props = ET.Element("properties")
        add_prop(props, "CHEF:creator", "admin")
        add_prop(props, "DAV:displayname", collection)
        add_prop(props, "CHEF:modifiedby", "admin")
        add_prop(props, "CHEF:description", "")
        add_prop(props, "CHEF:is-collection", "true")
        add_prop(props, "DAV:getlastmodified", "20240309112237083")
        add_prop(props, "SAKAI:conditionalrelease", "false")
        add_prop(props, "DAV:creationdate", "20240309112237081")
        add_prop(props, "SAKAI:conditionalNotificationId", "")

        collection_el.append(props)
        content_container.append(collection_el)

    # Iterate
    for attach_id in move_list:
        print(f"Moving {attach_id} to {move_list[attach_id]})")

        attach_item = attach_root.find(f".//resource[@id='{attach_id}']")
        if attach_item is not None:
            # Move it to content

            content_item = copy.deepcopy(attach_item)

            new_id = move_list[attach_id]
            rel_id = new_id.replace(f"/group/{SITE_ID}/","")

            content_item.set('id', new_id)
            content_item.set('rel-id', rel_id)

            # Add it to content, remove it from attachment
            content_container.append(content_item)
            attach_container.remove(attach_item)

            rewrite = True
        else:
            raise Exception(f"not found! {attach_id}")

    # Rewrite both
    if rewrite:
        content_tree.write(content_src, encoding='utf-8', xml_declaration=True)
        attach_tree.write(attach_src, encoding='utf-8', xml_declaration=True)

    return
