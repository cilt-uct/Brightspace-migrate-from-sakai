import os
import sys
import base64
import json
import lxml.etree as ET

from bs4 import BeautifulSoup
from urllib.parse import unquote

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

from lib.resources import get_resource_ids

# A1 Lessons pages more than 3 levels
#  in: site_folder
# TODO - incomplete
def a1(site_folder):
    file = "lessonbuilder.xml"
    file_path = os.path.join(site_folder, file)
    tree = ET.parse(file_path)
    root = tree.getroot()

    for element in root.findall(
            'org.sakaiproject.lessonbuildertool.service.LessonBuilderEntityProducer/lessonbuilder/'):
        # only check withing 'page' elements
        if element.tag == "page":
            # find item element(s)
            item = element.find('item')
            # if __debug__: print('item', item)
            # see if any 'item' element(s) exists
            if item is None:
                continue
            else:
                # iterate through all items
                outline = ""
                for _item in element:
                    type = _item.get('type')
                    name = _item.get('name')
                    #sequence = _item.get('sequence')
                    if type == "2":
                        outline += name if len(outline) == 0 else ";" + name


# A2 Discussion links on Lessons on the topic level
#  in: site_folder
def a2(site_folder):
    file = "lessonbuilder.xml"
    file_path = os.path.join(site_folder, file)
    tree = ET.parse(file_path)
    root = tree.getroot()

    for element in root.findall(
            'org.sakaiproject.lessonbuildertool.service.LessonBuilderEntityProducer/lessonbuilder/'):
        # only check withing 'page' elements
        if element.tag == "page":
            # find item element(s)
            item = element.find('item')
            # see if any 'item' element(s) exists
            if item is None:
                continue
            else:
                # iterate through all items
                for _item in element:
                    sakaiid = _item.get('sakaiid')
                    if 'forum_topic' in sakaiid:
                        return True


# A3 Discussion links on Lessons on the forum level
#  in: site_folder
def a3(site_folder):
    file = "lessonbuilder.xml"
    file_path = os.path.join(site_folder, file)
    tree = ET.parse(file_path)
    root = tree.getroot()

    for element in root.findall(
            'org.sakaiproject.lessonbuildertool.service.LessonBuilderEntityProducer/lessonbuilder/'):
        # only check withing 'page' elements
        if element.tag == "page":
            # find item element(s)
            item = element.find('item')
            # see if any 'item' element(s) exists
            if item is None:
                continue
            else:
                # iterate through all items
                for _item in element:
                    sakaiid = _item.get('sakaiid')
                    if 'forum_forum' in sakaiid:
                        return True


# AMA-352 Lessons hidden page
def a5(lessons_soup, site_soup):
    if lessons_soup.find("page", attrs={"hidden": "true"}):
        return True
    tools = site_soup.find_all("tool", attrs={"toolId": "sakai.lessonbuildertool"})
    for tool in tools:
        if tool.find("property", attrs={"name": "sakai-portal:visible", "value": "ZmFsc2U="}):
            return True


# A6 Lessons items optional descriptions
#  in: site_folder
def a6(site_folder):
    file = "lessonbuilder.xml"
    file_path = os.path.join(site_folder, file)
    tree = ET.parse(file_path)
    root = tree.getroot()

    for element in root.findall(
            'org.sakaiproject.lessonbuildertool.service.LessonBuilderEntityProducer/lessonbuilder/'):
        # only check withing 'page' elements
        if element.tag == "page":
            # find item element(s)
            item = element.find('item')
            # see if any 'item' element(s) exists
            if item is None:
                continue
            else:
                # iterate through all items
                for _item in element:
                    description = _item.get('description')
                    if len(description or '') > 0:
                        return True


# A9 Manual (static) hyperlinks in text that link to Sakai
#  in: site_folder
def a9(site_folder, sakai_url):
    file = "lessonbuilder.xml"
    file_path = os.path.join(site_folder, file)
    tree = ET.parse(file_path)
    root = tree.getroot()

    for element in root.findall(
            'org.sakaiproject.lessonbuildertool.service.LessonBuilderEntityProducer/lessonbuilder/'):
        # only check withing 'page' elements
        if element.tag == "page":
            # find item element(s)
            item = element.find('item')
            # see if any 'item' element(s) exists
            if item is None:
                continue
            else:
                # iterate through all items
                for _item in element:
                    html = _item.get('html')
                    if html is not None:
                        if sakai_url in html:
                            return True

# AMA-353 Lessons availability dates
def a10(lessons_soup):
    if len(lessons_soup.select("[releasedate]")):
        return True

# AMA-262 Lessons question with correct answer
def lessons_question_correct(lessons_soup):
    for question in lessons_soup.find_all("item", attrs={"type": "11"}):
        qJson = question.find("attributes").get_text()
        qAttr = json.loads(qJson)
        if 'answers' in qAttr:
            for answer in qAttr['answers']:
                if answer['correct']:
                    return True

# AMA-726 Flag highlighted links in Lessons html content (replaces a9)
# data-type:link attribute is set by the workflow operation lessonbuilder_highlight_tools
def lessons_hyperlinks(lessons_soup):
    data = set()

    items = lessons_soup.find_all("item", attrs={"type": "5"})
    for item in items:
        parsed_html = BeautifulSoup(item.attrs['html'], 'html.parser')
        link = parsed_html.find(attrs={"data-type": "link"})
        parent = lessons_soup.find_all('page', attrs={'pageid': item['pageId']})
        if len(parent) > 0 and link:
            title = parent[0]['title']
            data.add(title)

    if len(data) > 0:
        return sorted(data)
    else:
        return None

# AMA-726 Flag highlighted tool names in Lessons html content
# data-type:tool attribute is set by the workflow operation lessonbuilder_highlight_external_links
def lessons_tools(lessons_soup):
    data = set()

    items = lessons_soup.find_all("item", attrs={"type": "5"})
    for item in items:
        parsed_html = BeautifulSoup(item.attrs['html'], 'html.parser')
        tool = parsed_html.find("span", attrs={"data-type": "tool"})
        parent = lessons_soup.find_all('page', attrs={'pageid': item['pageId']})
        if len(parent) > 0 and tool:
            title = parent[0]['title']
            data.add(title)

    if len(data) > 0:
        return sorted(data)
    else:
        return None

# AMA-716 Flag embedded folder lists
# data-type:folder-list attribute is set by the workflow operation lessonbuilder_merge_items
def lessons_folder_list(lessons_soup):
    data = set()

    items = lessons_soup.find_all("item", attrs={"type": "5"})
    for item in items:
        parsed_html = BeautifulSoup(item.attrs['html'], 'html.parser')
        tool = parsed_html.find("div", attrs={"data-type": "folder-list"})
        parent = lessons_soup.find_all('page', attrs={'pageid': item['pageId']})
        if len(parent) > 0 and tool:
            title = parent[0]['title']
            data.add(title)

    if len(data) > 0:
        return sorted(data)
    else:
        return None

def lessons_embedded_content(lessons_soup):
    data = set()

    items = lessons_soup.find_all("item", attrs={"type": "5"})
    for item in items:
        parsed_html = BeautifulSoup(item.attrs['html'], 'html.parser')
        tool = parsed_html.find("p", attrs={"data-type": "placeholder"})
        parent = lessons_soup.find_all('page', attrs={'pageid': item['pageId']})
        if len(parent) > 0 and tool:
            title = parent[0]['title']
            data.add(title)

    if len(data) > 0:
        return sorted(data)
    else:
        return None

def lessons_missing_content(lessons_soup):
    data = set()

    items = lessons_soup.find_all("item", attrs={"type": "5"})
    for item in items:
        parsed_html = BeautifulSoup(item.attrs['html'], 'html.parser')
        tool = parsed_html.find("p", attrs={"data-type": "missing-content"})
        parent = lessons_soup.find_all('page', attrs={'pageid': item['pageId']})
        if len(parent) > 0 and tool:
            title = parent[0]['title']
            data.add(title)

    if len(data) > 0:
        return sorted(data)
    else:
        return None

# B1 Resources - Hidden folders and files
#  in: content_soup
def b1(content_soup):
    elements = content_soup.find_all(["collection", "resource"])
    for element in elements:
        sakai_hidden = element.get('hidden')
        if sakai_hidden == "true":
            return True
        if element.find("property", attrs={"name": "SAKAI:hidden_accessible_content", "value": "dHJ1ZQ=="}):
            return True


# B2 Folder structure more than 3 levels
#  in: site_folder
def b2(site_folder):
    file = "content.xml"
    file_path = os.path.join(site_folder, file)

    with open(file_path) as fp:
        soup = BeautifulSoup(fp, 'xml')
        items = soup.find_all("collection")
        # iterate through all collection items
        for collection in items:
            rel_id = collection.get('rel-id')
            if rel_id.count('/') > 3:
                return True


# B3 Turnitin enabled on Assignment
#  in: site_folder
def b3(assignment_soup):
    assignments = assignment_soup.find_all("Assignment")
    for assignment in assignments:
        contentReview = assignment.find('contentReview')
        if contentReview is not None:
            if contentReview.get_text() == "true":
                return True


# B4 Resubmissions allowed
#  in: site_folder
def b4(site_folder):
    file = "assignment.xml"
    file_path = os.path.join(site_folder, file)

    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        items = soup.find_all("Assignment")
        # iterate through all collection items
        for collection in items:
            allow_resubmit_number = collection.find('allow_resubmit_number')
            if allow_resubmit_number is not None:
                return True

# B5 Assignments anonymous grading
def b5(assignment_soup):
    assignments = assignment_soup.find_all("Assignment")
    for assignment in assignments:
        anonGrading = assignment.find("new_assignment_check_anonymous_grading")
        if anonGrading is not None:
            if anonGrading.get_text() == "true":
                return True

# B6 Assignments with peer review enabled
#  in: site_folder
def b6(site_folder):
    file = "assignment.xml"
    file_path = os.path.join(site_folder, file)

    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        items = soup.find_all("Assignment")
        # iterate through all collection items
        for collection in items:
            allowPeerAssessment = collection.find('allowPeerAssessment')
            if allowPeerAssessment is not None:
                if allowPeerAssessment.text == "true":
                    return True


# B7 Honour / Honor pledge (Assignments)
#  in: site_folder
def b7(site_folder):
    file = "assignment.xml"
    file_path = os.path.join(site_folder, file)
    # print(file_path)

    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        items = soup.find_all("Assignment")
        # iterate through all collection items
        for collection in items:
            honorPledge = collection.find('honorPledge')
            if honorPledge is not None:
                if honorPledge.text == "true":
                    return True

# B8 Assignments model answers
def b8(assignment_soup):
    if assignment_soup.find("ModelAnswer") or assignment_soup.find("PrivateNote") or assignment_soup.find("AllPurposeItem"):
        return True

# B9 Assignments linked to Gradebook
def b9(assignment_soup):
    assignments = assignment_soup.find_all("Assignment")
    for assignment in assignments:
        gbLink = assignment.find("prop_new_assignment_add_to_gradebook")
        if gbLink is not None:
            if gbLink.get_text():
                return True

# B10 Assignments group-scoped
def b10(assignment_soup):
    assignments = assignment_soup.find_all("Assignment")
    for assignment in assignments:
        isGroup = assignment.find("isGroup")
        typeOfAccess = assignment.find("typeOfAccess")
        if isGroup and typeOfAccess and isGroup.get_text() == "false" and typeOfAccess.get_text() == "GROUP":
            return True

# B11 Assignments group submission
def b11(assignment_soup):
    assignments = assignment_soup.find_all("Assignment")
    for assignment in assignments:
        isGroup = assignment.find("isGroup")
        typeOfAccess = assignment.find("typeOfAccess")
        if isGroup and typeOfAccess and isGroup.get_text() == "true" and typeOfAccess.get_text() == "GROUP":
            return True


# B12 Resources - Files or Folders only available on certain dates
#  in: content_soup
def b12(content_soup):
    elements = content_soup.find_all(["collection", "resource"])
    for element in elements:
        if element.has_attr('sakai:release_date') or element.has_attr('sakai:retract_date'):
            return True


# AMA-390: B13 Resources - Group-scoped folders/files
#  in: content_soup
def b13(content_soup):
    if content_soup.find(["collection", "resource"], attrs={"sakai:access_mode": "grouped"}):
        return True


# AMA-77 T&Q assessments with duration
def c1(site_folder, samigo_soup):
        items = samigo_soup.find_all("assessment")
        # iterate through all assessment items
        for collection in items:
            id = collection.get('id')
            # fetch each assessment
            assignment_file_name = 'assessment' + id + '.xml'
            file_path_assignment = os.path.join(site_folder, 'qti', assignment_file_name)
            with open(file_path_assignment, "r", encoding="utf8") as _fp:
                _soup = BeautifulSoup(_fp, 'xml')
                assessment = _soup.find("assessment")
                duration = assessment.find("duration", recursive = False)
                if duration.get_text():
                    return True

# AMA-332 T&Q descriptions
def c2(site_folder, samigo_soup):
        items = samigo_soup.find_all("assessment")
        for collection in items:
            file_path = os.path.join(site_folder, 'qti', 'assessment' + collection.get('id') + '.xml')
            tree = ET.parse(file_path)
            desc = tree.find("./assessment/presentation_material/flow_mat/material/mattext")
            if desc is not None and desc.text and desc.text.strip():
                return True

# AMA-333 T&Q description with attachments
def c3(site_folder, samigo_soup):
        items = samigo_soup.find_all("assessment")
        for collection in items:
            file_path = os.path.join(site_folder, 'qti', 'assessment' + collection.get('id') + '.xml')
            tree = ET.parse(file_path)
            root = tree.getroot()
            for qtim in root.findall("./assessment/qtimetadata/qtimetadatafield"):
                if qtim.find("fieldlabel").text == "ATTACHMENT" and qtim.find("fieldentry").text:
                    return True

# AMA-335 T&Q descriptions in parts
def c7a(site_folder, samigo_soup):
        items = samigo_soup.find_all("assessment")
        for collection in items:
            file_path = os.path.join(site_folder, 'qti', 'assessment' + collection.get('id') + '.xml')
            tree = ET.parse(file_path)
            root = tree.getroot()
            for section_qtim in root.findall("./assessment/section/qtimetadata"):
                for qtim in section_qtim.findall("qtimetadatafield"):
                    if qtim.find("fieldlabel").text == "SECTION_INFORMATION" and qtim.find("fieldentry").text:
                        return True

def c7b(site_folder, samigo_soup):
        items = samigo_soup.find_all("assessment")
        for collection in items:
            file_path = os.path.join(site_folder, 'qti', 'assessment' + collection.get('id') + '.xml')
            tree = ET.parse(file_path)
            root = tree.getroot()
            for section_qtim in root.findall("./assessment/section/qtimetadata"):
                for qtim in section_qtim.findall("qtimetadatafield"):
                    if qtim.find("fieldlabel").text == "ATTACHMENT" and qtim.find("fieldentry").text:
                        return True

# AMA-121 Inline images in T&Q questions that aren't in this site's Resources
# Attachments should already have been processed and moved into content
def c8(site_folder, samigo_soup, sakai_url):
    data = set()

    content_src = f'{site_folder}/content.xml'
    content_ids = get_resource_ids(content_src)

    # Questions
    items = samigo_soup.find_all("assessment")
    for collection in items:
        file_path = os.path.join(site_folder, 'qti', 'assessment' + collection.get('id') + '.xml')
        tree = ET.parse(file_path)
        root = tree.getroot()

        # <questestinterop><assessment ident="160024" title="Case 10 Urinary System Histology quiz">
        title = root.find(".//assessment").get("title")

        for item in root.findall(".//mattext[@texttype='text/plain']"):
            # could be plain text so check that it at least contains an image tag
            if item.text and "<img" in item.text:
                html = BeautifulSoup(item.text, 'html.parser')
                for el in html.findAll("img"):
                    img_src = el.get('src')
                    if img_src and img_src.startswith(f"{sakai_url}/access/content/"):
                        img_id = unquote(img_src.replace(f"{sakai_url}/access/content",""))
                        if img_id not in content_ids:
                            print(f"{img_id} not found in content")
                            data.add(title)

    # Question Pools
    file = "samigo_question_pools.xml"
    file_path = os.path.join(site_folder, file)
    if os.path.isfile(file_path):
        tree = ET.parse(file_path)
        root = tree.getroot()
        for qp in root.findall(".//QuestionPool"):
            qp_title = qp.get("title")
            # <QuestionPool id="11771" ownerId="d21166da-9b65-4457-9cca-148f4c5e4ee9" sourcebank_ref="11771::Yr 2 July Immunology mcq" title="Yr 2 July Immunology mcq">
            for item in qp.findall(".//mattext"):
                if item.text and "<img" in item.text:
                    html = BeautifulSoup(item.text.replace("<![CDATA[", "").replace("]]>", ""), 'html.parser')
                    for el in html.findAll("img"):
                        img_src = el.get('src')
                        if img_src and img_src.startswith(f"{sakai_url}/access/content/"):
                            img_id = unquote(img_src.replace(f"{sakai_url}/access/content",""))
                            if img_id not in content_ids:
                                print(f"{img_id} not found in content")
                                data.add(f"Question Pool: {qp_title}")

    if len(data) > 0:
        return sorted(data)
    else:
        return None

# C9 Question pools
#  in: site_folder
def c9(site_folder):
    file = "samigo_question_pools.xml"
    file_path = os.path.join(site_folder, file)

    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf8") as fp:
            soup = BeautifulSoup(fp, 'xml')
            qp = soup.find_all("QuestionPool")
            if (len(qp) > 0):
                return True

# C10 Hotspot question
#  in: site_folder, samigo_question_pools soup, samigo soup
def c10(site_folder, samigo_question_pools_soup, samigo_soup):
    return_value = None

    if samigo_question_pools_soup is not None:
        questionPools = samigo_question_pools_soup.find_all("QuestionPool")
        for questionPool in questionPools:
            items = questionPool.find_all("item")
            for item in items:
                title = item.get('title')
                if title == "Hotspot Question":
                    return_value = True
                    continue

    if return_value is None:
        if samigo_soup is not None:
            assessments = samigo_soup.find_all("assessment")
            # iterate through all assessment items
            for assessment in assessments:
                id = assessment.get('id')
                # fetch each assessment
                assignment_file_name = 'assessment' + id + '.xml'
                file_path_assignment = os.path.join(site_folder, 'qti', assignment_file_name)
                with open(file_path_assignment, "r", encoding="utf8") as _fp:
                    soup = BeautifulSoup(_fp, 'xml')
                    items = soup.find_all("item")
                    for item in items:
                        title = item.get('title')
                        if title == "Hotspot Question":
                            return_value = True
                            continue

    return return_value


# C11 Audio recording question
#  in: site_folder
def c11(site_folder, samigo_soup):

        items = samigo_soup.find_all("assessment")

        # iterate through all collection items
        for collection in items:
            id = collection.get('id')

            # fetch each assessment
            assignment_file_name = 'assessment' + id + '.xml'
            file_path_assignment = os.path.join(site_folder, 'qti', assignment_file_name)
            with open(file_path_assignment, "r", encoding="utf8") as _fp:
                _soup = BeautifulSoup(_fp, 'xml')
                _items = _soup.find_all("item")
                for _collection in _items:
                    fieldentry = _collection.find('fieldentry')
                    if fieldentry.text == "Audio Recording":
                        return True

# C12 Extended matching item
#  in: site_folder
def c12(site_folder, samigo_soup):

        items = samigo_soup.find_all("assessment")

        # iterate through all collection items
        for collection in items:
            id = collection.get('id')

            # fetch each assessment
            assignment_file_name = 'assessment' + id + '.xml'
            file_path_assignment = os.path.join(site_folder, 'qti', assignment_file_name)
            with open(file_path_assignment, "r", encoding="utf8") as _fp:
                _soup = BeautifulSoup(_fp, 'xml')
                _items = _soup.find_all("item")
                # iterate through all collection items
                for _collection in _items:
                    fieldentry = _collection.find('fieldentry')
                    if fieldentry.text == "Extended Matching Items":
                        return True


# C13 MCQ with negative marking
#  in: site_folder
def c13(site_folder, samigo_soup):
        items = samigo_soup.find_all("assessment")
        # iterate through all assessment items
        for collection in items:
            id = collection.get('id')
            # fetch each assessment
            assignment_file_name = 'assessment' + id + '.xml'
            file_path_assignment = os.path.join(site_folder, 'qti', assignment_file_name)
            with open(file_path_assignment, "r", encoding="utf8") as _fp:
                _soup = BeautifulSoup(_fp, 'xml')
                _items = _soup.find_all("item")
                for _collection in _items:
                    fieldentry = _collection.find('fieldentry')
                    if fieldentry.text == "Multiple Choice":
                        decvar = _collection.find('decvar')
                        minvalue = decvar.get('minvalue')
                        if minvalue != "0.0":
                            return True


# C14 Calculated questions - Scientific notation
#  in: site_folder
def c14(site_folder, samigo_soup):
        data = set()
        items = samigo_soup.find_all("assessment")
        # iterate through all assessment items
        for collection in items:
            id = collection.get('id')
            # fetch each assessment
            assignment_file_name = 'assessment' + id + '.xml'
            file_path_assignment = os.path.join(site_folder, 'qti', assignment_file_name)
            with open(file_path_assignment, "r", encoding="utf8") as _fp:
                _soup = BeautifulSoup(_fp, 'xml')
                _title = _soup.find("assessment")
                _items = _soup.find_all("item")
                for _collection in _items:
                    fieldentry = _collection.find('fieldentry')
                    if fieldentry.text == "Calculated Question":
                        formulas = _collection.find('formulas')
                        if formulas is not None:
                            data.add(f'{_title.attrs["title"]}')

        if len(data) > 0:
            return sorted(data)
        else:
            return None


# C15 Numeric response question
#  in: site_folder
def c15(site_folder, samigo_soup):
        items = samigo_soup.find_all("assessment")
        # iterate through all assessment items
        for collection in items:
            id = collection.get('id')
            # fetch each assessment
            assignment_file_name = 'assessment' + id + '.xml'
            file_path_assignment = os.path.join(site_folder, 'qti', assignment_file_name)
            with open(file_path_assignment, "r", encoding="utf8") as _fp:
                _soup = BeautifulSoup(_fp, 'xml')
                _items = _soup.find_all("item")
                for _collection in _items:
                    fieldentry = _collection.find('fieldentry')
                    if fieldentry.text == "Numeric Response":
                        return True


# C16 Fill in the blank
#  in: site_folder
def c16(site_folder, samigo_soup):
        data = set()
        items = samigo_soup.find_all("assessment")
        # iterate through all assessment items
        for collection in items:
            id = collection.get('id')
            # fetch each assessment
            assignment_file_name = 'assessment' + id + '.xml'
            file_path_assignment = os.path.join(site_folder, 'qti', assignment_file_name)
            with open(file_path_assignment, "r", encoding="utf8") as _fp:
                _soup = BeautifulSoup(_fp, 'xml')
                _title = _soup.find("assessment")
                _items = _soup.find_all("item")
                for _collection in _items:
                    fieldentry = _collection.find('fieldentry')
                    if fieldentry.text == "Fill In the Blank":
                        data.add(f'{_title.attrs["title"]}')

        if len(data) > 0:
            return sorted(data)
        else:
            return None


# C17 Question level feedback
#  in: site_folder
# def c17(site_folder):
def c17(site_folder, samigo_soup):
        items = samigo_soup.find_all("assessment")
        # iterate through all assessment items
        for collection in items:
            id = collection.get('id')
            # fetch each assessment
            assignment_file_name = 'assessment' + id + '.xml'
            file_path_assignment = os.path.join(site_folder, 'qti', assignment_file_name)
            with open(file_path_assignment, "r", encoding="utf8") as _fp:
                _soup = BeautifulSoup(_fp, 'xml')
                _items = _soup.find_all("item")
                for _collection in _items:
                    itemfeedback = _collection.find('itemfeedback')
                    if itemfeedback is not None:
                        _mattext = itemfeedback.find('mattext')
                        if _mattext is not None:
                            if len(_mattext.text) > 0:
                                return True

# AMA-337 T&Q anonymous grading
def c18(site_folder, samigo_soup):
        items = samigo_soup.find_all("assessment")
        # iterate through all assessment items
        for collection in items:
            id = collection.get('id')
            # fetch each assessment
            assignment_file_name = 'assessment' + id + '.xml'
            file_path_assignment = os.path.join(site_folder, 'qti', assignment_file_name)
            with open(file_path_assignment, "r", encoding="utf8") as _fp:
                _soup = BeautifulSoup(_fp, 'xml')
                _qmi = _soup.find_all("qtimetadatafield")
                for metadata in _qmi:
                    if metadata.find("fieldlabel").get_text() == "ANONYMOUS_GRADING" and metadata.find("fieldentry").get_text() == "True":
                        return True


# AMA-343 C19 Test & Quizzes linked to Gradebook
#  in: gradebook_soup
def c19(gradebook_soup):
    if gradebook_soup.find("GradebookItem", attrs={"externalAppName": "sakai.samigo"}):
        return True


# D1 Forum / Topic attachments
def d1(discussions_soup):

    forums = discussions_soup.find_all("discussion_forum")
    for forum in forums:
        if forum.find("attachment", recursive=False):
            return True

    topics = discussions_soup.find_all("discussion_topic")
    for topic in topics:
        if topic.find("attachment", recursive=False):
            return True

# D3 Forum / Topic availability dates
def d3(discussions_soup):
    if len(discussions_soup.select("[available_open]")) or len(discussions_soup.select("[available_close]")):
        return True

# D5 Forum and Topic gradebook settings
def d5(discussions_soup):
    if len(discussions_soup.select("[grade_assignment]")):
        return True

# AMA-355 Gradebook weightings
def e1(gradebook_soup):
    category_type = gradebook_soup.find("CategoryType")
    if category_type and category_type.get_text() == "WEIGHTED_CATEGORIES_APPLIED":
        return True

# Detect custom CSS
#  in: site_folder
def detect_custom_css(site_folder):
    file = "lessonbuilder.xml"
    file_path = os.path.join(site_folder, file)

    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        pages = soup.findAll('page')
        for page in pages:
            csssheet = page.get("csssheet")
            if csssheet is not None:
                return True


# AMA-437 Lessons use checklists
#  in: lessons_soup
def lessons_use_checklists(lessons_soup):
    if lessons_soup.find("item", attrs={"type": "15"}):
        return True


# AMA-656 Lessons uses comments
def lessons_use_comments(lessons_soup):
    if lessons_soup.find("item", attrs={"type": "9"}):
        return True


# AMA-351 Lessons use prerequisites
#  in: lessons_soup
def a4(lessons_soup):
    if lessons_soup.find("item", attrs={"prerequisite": "true"}):
        return True


# Detect sections
#  in: site_folder
def use_of_sections(site_folder):
    file = "site.xml"
    file_path = os.path.join(site_folder, file)

    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        site = soup.find("site")
        groups = site.find("groups")
        if groups and groups.find("property", attrs={"name": "sections_category"}):
            return True

# Detect groups
#  in: site_folder
def use_of_groups(site_folder):
    file = "site.xml"
    file_path = os.path.join(site_folder, file)

    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        site = soup.find("site")
        groups = site.find("groups")
        if groups and groups.find("property", attrs={"name": "group_prop_wsetup_created"}):
            return True

# AMA-363 displaynames in files
def content_displayname_files(content_soup, ignored_collections):
    contents = content_soup.find_all("resource")
    for content in contents:
        filepath, filename = os.path.split(content.get("rel-id"))
        top_folder = filepath.split("/")[0]
        # Skip attachments in designated collections that we create
        if top_folder in ignored_collections:
            continue
        displayprop = content.find("property", attrs={"name": "DAV:displayname"})
        displayname = str(base64.b64decode(displayprop.get("value")).decode('utf-8'))
        if filename != "Site Information.html" and filename != displayname:
            print(f"filename {filename} displays as {displayname}")
            return True

# AMA-363 displaynames in folders
def content_displayname_folders(content_soup):
    contents = content_soup.find_all("collection")
    for content in contents:
        folderpath, foldername = os.path.split("/" + content.get("rel-id")[:-1])
        if foldername:
            displayprop = content.find("property", attrs={"name": "DAV:displayname"})
            if displayprop:
                displayname = str(base64.b64decode(displayprop.get("value")).decode('utf-8'))
                if foldername != displayname:
                    # print(f"folder {foldername} displays as {displayname}")
                    return True

# External Tools
def external_tools(site_soup, lti_soup):
    # toolId="sakai.basiclti" OR
    # toolId="sakai.web.168" in site with a property name=source value decodes to /access/basiclti/...

    if site_soup.find("tool", attrs={"toolId": "sakai.basiclti"}):
        return True

    for webtool in site_soup.find_all("tool", attrs={"toolId": "sakai.web.168"}):
        websource = webtool.find("property", attrs={"name": "source"})
        if websource:
            weblaunch = str(base64.b64decode(websource.get("value")).decode('utf-8'))
            if weblaunch.startswith("/access/basiclti/"):
                return True


# AMA-316 Disallowed extensions
def disallowed_extensions(content_soup, attachment_soup, restricted_ext):

    disallowed = restricted_ext['RESTRICTED_EXT']

    # Find extensions in Resources and check against disallowed list
    if content_soup:
        for item in content_soup.find_all("resource"):
            file_name, file_extension = os.path.splitext(item.get('id'))
            if file_extension and file_extension.upper().replace(".","") in disallowed:
                return True

    # Find extensions in attachments and check against disallowed list
    if attachment_soup:
        for item in attachment_soup.find_all("resource"):
            file_name, file_extension = os.path.splitext(item.get('id'))
            if file_extension and file_extension.upper().replace(".","") in disallowed:
                return True

# AMA-552 Check fo unsupported video and audio types
def supported_media_types(content_soup, attachment_soup, restricted_ext):

    supported_audio = restricted_ext['SUPPORTED_AUDIO']
    supported_video = restricted_ext['SUPPORTED_VIDEO']

    # Find extensions in Resources and check against disallowed list
    if content_soup:
        for item in content_soup.find_all("resource"):
            file_name, file_extension = os.path.splitext(item.get('id'))
            file_extension = file_extension.upper().replace(".","")

            if item.get('content-type').startswith('audio/') and file_extension not in supported_audio:
                return True

            if item.get('content-type').startswith('video/') and file_extension not in supported_video:
                return True

    # Not necessary to check attachments as these don't cause failures

    return


# AMA-182 Check if rubrics have been used in site tools
def rubrics_used(site_soup, rubric_folder):

    rubric_tool_file = f"{rubric_folder}rubric_tools.json"
    data = set()

    if not os.path.exists(rubric_tool_file):
        return

    with open(rubric_tool_file) as json_file:
        rubricAssoc = json.load(json_file)['rubric_tool']

    for ra in rubricAssoc:
        toolId = ra['toolId']
        if toolId == "sakai.assignment":
            toolId = "sakai.assignment.grades"

        tool = site_soup.find("tool", attrs={"toolId": toolId})
        if tool:
            toolName = tool.get('title')
        else:
            toolName = ra['toolId']

        data.add(f"{ra['title']} used in {toolName}")

    if len(data) > 0:
        return sorted(data)
    else:
        return None


# AMA-443 Check if rubrics have been used in site tools
# Negative point values replaced with level_value="0"
def rubric_negative_points(site_soup, rubric_folder):

    rubric_file = f"{rubric_folder}rubrics_d2l.xml"

    if not os.path.exists(rubric_file):
        return None

    tree = ET.parse(rubric_file)
    root = tree.getroot()

    if root.find(".//level[@level_value='0']") is not None:
        return True

    return False


# AMA-443 Check if rubric descriptions have been truncated
def rubric_truncated(site_soup, rubric_folder):

    rubric_file = f"{rubric_folder}rubrics_d2l.xml"

    if not os.path.exists(rubric_file):
        return None

    tree = ET.parse(rubric_file)
    root = tree.getroot()

    for el_name in root.xpath(".//criteria_group | .//criterion"):
        if el_name.get('name').endswith(" ..."):
            return True

    return False
