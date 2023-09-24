import argparse

from lib.utils import *

def run(site_id: str, org_id: str, app: dict):
    logging.info('Replace placeholders with multimedia links for org_id: {}'.format(org_id))
    site_folder = APP['archive_folder']

    xml_src = r'{}{}-archive/lessonbuilder.xml'.format(site_folder, site_id)
    xml_old = r'{}{}-archive/lessonbuilder.old'.format(site_folder, site_id)
    shutil.copyfile(xml_src, xml_old)

    remove_unwanted_characters(xml_src)

    file_path = os.path.join(site_folder, xml_src)

    with open(file_path, "r", encoding="utf8") as fp:
        soup = BeautifulSoup(fp, 'xml')
        pages = soup.find_all('page')
        for page in pages:
            items = page.find_all('item', attrs={"type": "5"})
            for item in items:
                html = BeautifulSoup(item.attrs['html'], 'html')
                placeholder_found = html.find('p', attrs={"data-type": "placeholder"})
                if placeholder_found:
                    endpoint = "{}{}{}".format(APP['middleware']['base_url'], APP['middleware']['content_root_url'], org_id)
                    response = middleware_api(APP, endpoint)
                    pages = response['data']
                    for page in pages:
                        page_html = page['Description']['Html']
                        if page['Type'] == 0 and page_html:
                            soup_html = BeautifulSoup(page_html, 'html')
                            placeholders = soup_html.find_all('p', attrs={"data-type": "placeholder"})
                            updated = False
                            for placeholder in placeholders:
                                sakai_id = placeholder.attrs['data-sakaiid']
                                file_name = os.path.basename(sakai_id)
                                files = page['Structure']
                                for file in files:
                                    if file_name == file['Title']:
                                        href = f'{APP["brightspace_url"]}{APP["brightspace_lessons"]}{org_id}/topics/{file["Id"]}'
                                        link = BeautifulSoup(f'<p><a href="{href}">{file["Title"]}</a></p>', 'html.parser')
                                        placeholder.replace_with(link)
                                        updated = True

                            if updated:
                                update_endpoint = "{}{}".format(APP['middleware']['base_url'], APP['middleware']['update_content_url'])
                                middleware_api(APP, update_endpoint, payload_data={'org_id': org_id, 'parent_id': page['Id'], 'description': soup_html})




def main():
    global APP
    parser = argparse.ArgumentParser(description="This script uploads rubrics",
                                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("SITE_ID", help="The SITE_ID to process")
    parser.add_argument("IMPORT_ID", help="The org unit id of the imported site")
    parser.add_argument('-d', '--debug', action='store_true')
    args = vars(parser.parse_args())

    APP['debug'] = APP['debug'] or args['debug']

    run(site_id=args['SITE_ID'], org_id=args['IMPORT_ID'], app=APP)

if __name__ == '__main__':
    main()