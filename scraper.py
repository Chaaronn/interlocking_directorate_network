import requests, re
from datetime import datetime


api_key = 'ecd64772-ee19-4ff2-a5ed-bc7142a59aed'
ch_base_url = 'https://api.company-information.service.gov.uk/'

session = requests.Session()
session.auth= (api_key, "")

def search_ch(name):
    """
    Searches for a company on the Companies House API using the provided company name.

    Args:
        name (str): The name of the company to search for.

    Returns:
        dict: A dictionary containing the search results if the request is successful.
        If the request fails, it returns None and prints an error message.
    """
    headers = {"Authorization" : f"Basic {api_key}"}
    
    params = {"q" : name}

    url = ch_base_url + 'search/companies'

    r = session.get(url, headers=headers, params=params)
    if r.status_code == 200:
        return r.json()
    else:
        print(f"Call {params['q']} failed to {url} with code {r.status_code} and headers {r.headers}")
        return

def get_persons_with_control_info(company_link):

    headers = {"Authorization" : f"Basic {api_key}"}

    params = {"items_per_page" : '10',
              "start_index" : '0',
              "register_view": 'false'}

    url = ch_base_url + company_link + '/persons-with-significant-control'

    r = session.get(url, headers=headers, params=params)

    if r.status_code == 200:
        return r.json()
    else:
        print(f"Call failed to {url} with code {r.status_code} and headers {r.headers}")
        return None

def get_active_sig_persons_from_name(company_name):

    res = search_ch(company_name)

    company_link = res['items'][0]['links']['self']

    persons_sig = get_persons_with_control_info(company_link)

    active_count =  persons_sig['active_count']

    active_sig_persons = []

    for i in range(0, active_count):
        active_sig_persons.append(persons_sig['items'][i])

    return active_sig_persons

    #persons_names = persons_sig['items'][0]['name']

def get_entity_information(self_link):
    '''
    Returns info on corporate entities

    Input: self link from active_sig_entities
    '''

    res = session.get(ch_base_url + self_link)

    if res.status_code == 200:
        data = res.json()
        return data
    else:
        print('Error:', res.status_code)
        return None

def constuct_ch_link(company_number):
    new_url = f"find-and-update.company-information.service.gov.uk/company/{company_number}/"
    return new_url


def recusive_get_company_tree_from_sigs(company_name, start, end):
    start = int(start)
    end = int(end)

    search_result = search_ch(company_name)
    if not search_result:
        return []
    
    company_info = search_result['items'][0]
    company_number = company_info['company_number']
    company_name = company_info['title']

    sig_control_list = get_active_sig_persons_from_name(company_name)
    if not sig_control_list:
        return []

    entity_data = []
    visited_entities = set()

    def traverse_entities(entities, company_number, company_name):
        for entity in entities:
            
            try:
                start_date, end_date = datetime.strptime(entity['notified_on'], '%Y-%m-%d'), datetime.strptime(entity['ceased_on'], '%Y-%m-%d')
            except:
                start_date = datetime.strptime(entity['notified_on'], '%Y-%m-%d')
                end_date = datetime.now()

            if start_date.year <= end and end_date.year >= start:
                
                entity_info = get_entity_information(entity['links']['self'])

                if entity['etag'] not in visited_entities:

                    visited_entities.add(entity['etag'])
                    entity_data.append({
                        'company_id': company_number,
                        'company_name': company_name,
                        'etag': entity['etag'],
                        'name': entity['name'],
                        'start_date': start_date,
                        'end_date': end_date,
                        'nature_of_control': entity['natures_of_control'],
                        'link': constuct_ch_link(company_number)
                    })

                    other_sig_control_list = get_active_sig_persons_from_name(entity['name'])

                    # Potentially add in some validation on if individual or company here

                    if other_sig_control_list:
                        other_company_info = search_ch(entity['name'])['items'][0]
                        traverse_entities(other_sig_control_list, other_company_info['company_number'], other_company_info['title'])
    
    traverse_entities(sig_control_list, company_number, company_name)
    
    return entity_data