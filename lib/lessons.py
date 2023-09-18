import enum


class LessonType(enum.Enum):
    RESOURCE = '1'
    PAGE = '2'
    ASSIGNMENT = '3'
    ASSESSMENT = '4'
    TEXT = '5'
    URL = '6'
    MULTIMEDIA = '7'
    FORUM = '8'
    COMMENTS = '9'
    STUDENT_CONTENT = '10'
    QUESTION = '11'
    BLTI = '12'
    PEEREVAL = '13'
    BREAK = '14'
    RESOURCE_FOLDER = '20'
    CHECKLIST = '15'
    FORUM_SUMMARY = '16'
    ANNOUNCEMENTS = '17'
    TWITTER = '18'
    CALENDAR = '19'
