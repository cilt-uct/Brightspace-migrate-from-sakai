import argparse
import lib.utils

from config.logging_config import *
from lib.utils import *

def run(site_id: str, org_id: str, app: dict):
    logging.info('Replace placeholders with multimedia links for org_id: {}'.format(org_id))
    site_folder = app['archive_folder']

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(site_folder, site_id)

    remove_unwanted_characters(xml_src)

    file_path = os.path.join(site_folder, xml_src)

    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        lessons_pages = soup.find_all('page')
        for lessons_page in lessons_pages:
            items = lessons_page.find_all('item', attrs={"type": "5"})
            for item in items:
                html = BeautifulSoup(item.attrs['html'], 'html')
                placeholder_found = html.find('p', attrs={"data-type": "placeholder"})
                if placeholder_found:
                    endpoint = "{}{}{}".format(app['middleware']['base_url'], app['middleware']['content_root_url'], org_id)
                    response = lib.utils.middleware_api(app, endpoint)
                    unit_pages = response['data']
                    for unit_page in unit_pages:
                        page_html = unit_page['Description']['Html']
                        if unit_page['Type'] == 0 and page_html:
                            soup_html = BeautifulSoup(page_html, 'html')
                            placeholders = soup_html.find_all('p', attrs={"data-type": "placeholder"})
                            updated = False
                            for placeholder in placeholders:
                                file_name = placeholder.attrs['data-name']
                                files = unit_page['Structure']
                                for file in files:
                                    if file_name == file['Title']:
                                        topic_endpoint = "{}{}".format(app['middleware']['base_url'],
                                                                   app['middleware']['get_topics'].format(org_id))
                                        topics_response = lib.utils.middleware_api(app, topic_endpoint)
                                        topic = list(filter(lambda x: x['data']['Id'] == file['Id'], topics_response))[0]
                                        media_id = topic['data']['Url'].split(':')[-1].split('/')[0]

                                        link = BeautifulSoup(f'<p><iframe src="/d2l/wcs/mp/mediaplayer.d2l?ou=6606&amp;entryId={media_id}&amp;captionsEdit=False" title="{file_name}" width="700px" style="max-width: 100%; min-height: 340px; aspect-ratio: 700/393;" scrolling="no" frameborder="0" allowfullscreen="allowfullscreen" webkitallowfullscreen="true" mozallowfullscreen="true"></iframe></p>', 'html.parser')
                                        placeholder.replace_with(link)
                                        updated = True

                                    if updated:
                                        update_endpoint = "{}{}".format(app['middleware']['base_url'],
                                                                 app['middleware']['update_html_file'].format(org_id,
                                                                                                              file['Id']))
                                        lib.utils.middleware_api(app, update_endpoint, payload_data={'html': str(soup_html)})
                                        updated = False


def main():
    global APP
    parser = argparse.ArgumentParser(description="Check for placeholders in lessons and embed multimedia file",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("IMPORT_ID", help="The org unit id of the imported site")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(site_id=args['SITE_ID'], org_id=args['IMPORT_ID'], app=APP)


if __name__ == '__main__':
    main()
