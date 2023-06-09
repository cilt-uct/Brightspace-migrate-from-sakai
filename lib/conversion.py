import os
import base64
import json

from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

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
                    sequence = _item.get('sequence')
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
                    return True;


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
        return True;

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
            root = tree.getroot()
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

def c8(site_folder, samigo_soup, sakai_url):
        # Questions
        items = samigo_soup.find_all("assessment")
        for collection in items:
            file_path = os.path.join(site_folder, 'qti', 'assessment' + collection.get('id') + '.xml')
            tree = ET.parse(file_path)
            root = tree.getroot()
            for item in root.findall(".//mattext[@texttype='text/plain']"):
                # could be plain text so check that it at least contains an image tag
                if item.text and "<img" in item.text:
                    html = BeautifulSoup(item.text, 'html.parser')
                    for el in html.findAll("img"):
                        if el.get('src') and el.get('src').startswith(sakai_url):
                            return True

        # Question Pools
        file = "samigo_question_pools.xml"
        file_path = os.path.join(site_folder, file)
        if os.path.isfile(file_path):
            tree = ET.parse(file_path)
            root = tree.getroot()
            for item in root.findall(".//mattext"):
                if item.text and "<img" in item.text:
                    html = BeautifulSoup(item.text.replace("<![CDATA[", "").replace("]]>", ""), 'html.parser')
                    for el in html.findAll("img"):
                        if el.get('src') and el.get('src').startswith(sakai_url):
                            return True


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
                    if fieldentry.text == "Calculated Question":
                        formulas = _collection.find('formulas')
                        if formulas is not None:
                            return True


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
                    if fieldentry.text == "Fill In the Blank":
                        return True


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

    forums = discussions_soup.find_all("discussion_forum");
    for forum in forums:
        if forum.find("attachment", recursive=False):
            return True;

    topics = discussions_soup.find_all("discussion_topic");
    for topic in topics:
        if topic.find("attachment", recursive=False):
            return True;

# D3 Forum / Topic availability dates
def d3(discussions_soup):
    if len(discussions_soup.select("[available_open]")) or len(discussions_soup.select("[available_close]")):
        return True;

# D5 Forum and Topic gradebook settings
def d5(discussions_soup):
    if len(discussions_soup.select("[grade_assignment]")):
        return True;

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
def content_displayname_files(content_soup):
    contents = content_soup.find_all("resource")
    for content in contents:
        filepath, filename = os.path.split(content.get("rel-id"))
        displayprop = content.find("property", attrs={"name": "DAV:displayname"})
        displayname = str(base64.b64decode(displayprop.get("value")).decode('utf-8'))
        if filename != "Site Information.html" and filename != displayname:
            # print(f"filename {filename} displays as {displayname}")
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
    supported_video = restricted_ext['SUPPORTED_AUDIO']

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


def detect(soup, tool_id):
    items = soup.find_all("site")
    # site.xml seems to have only 1 site element within the main site element
    site = items[1]
    # print('site', site)
    items = soup.find_all("page")
    # iterate through all assessment items
    for page in items:
        # print('page', page)
        tools = page.find_all("tool")
        for tool in tools:
            # print('tool', tool)
            toolId = tool.get('toolId')
            # toolId = "sakai.syllabus"
            if toolId == tool_id:
                return True
