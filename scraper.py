import requests, re, os
from datetime import datetime


api_key = os.getenv('API_KEY')
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

def adv_search_ch(name_includes, name_excludes='', company_status='', company_subtype='', company_type='', 
                  dissolved_from='', dissolved_to='', incorporated_from='', incorporated_to='', location='',
                    sic_codes=''):
    """
    Advanced searches for a company on the Companies House API using the provided company details.

    Args:
        name_includes (str): Items within the company name (e.g., Knight, R&D etc.) Should normally be the full company name
        name_excludes (str): Items within the company name to exclude formsearch. Helpful when two companies have similar names.
        company_status (list): The company status advanced search filter. To search using multiple values, use a comma delimited list or multiple of the same key i.e. company_status=xxx&company_status=yyy
        sic_codes (list): The SIC codes advanced search filter. To search using multiple values, use a comma delimited list or multiple of the same key i.e. sic_codes=xxx&sic_codes=yyy 

    Returns:
        dict: A dictionary containing the search results if the request is successful.
        If the request fails, it returns None and prints an error message.
    """

    # Validate input types
    if not isinstance(name_includes, str) or not isinstance(name_excludes, str):
        raise ValueError("name_includes and name_excludes must be strings.")
    
    if not isinstance(company_status, (list, str)):
        raise ValueError("company_status must be a list or a comma-separated string.")
    
    if not isinstance(sic_codes, (list, str)):
        raise ValueError("sic_codes must be a list or a comma-separated string.")

    # Validate input lengths
    if len(name_includes) == 0 or len(name_excludes) == 0:
        raise ValueError("name_includes and name_excludes cannot be empty.")
    
    # Convert single string inputs to lists for consistency
    if isinstance(company_status, str):
        company_status = [company_status]
    if isinstance(sic_codes, str):
        sic_codes = [sic_codes]

    # Define acceptable values for validation
    valid_company_status = ["active", "dissolved", "liquidation", "open", "closed", "converted-closed",
                            "receivership", "administration", "insolvency-proceedings", "voluntary-arrangement",
                            "registered", "removed"]
    
    valid_company_types = ["private-unlimited", "ltd", "plc", "old-public-company", "private-limited-guarant-nsc-limited-exemption",
                           "limited-partnership", "private-limited-guarant-nsc", "converted-or-closed", "private-unlimited-nsc",
                           "private-limited-shares-section-30-exemption", "protected-cell-company", "assurance-company",
                           "oversea-company", "eeig", "icvc-securities", "icvc-warrant", "icvc-umbrella",
                           "registered-society-non-jurisdictional", "industrial-and-provident-society", "northern-ireland",
                           "northern-ireland-other", "royal-charter", "investment-company-with-variable-capital",
                           "unregistered-company", "llp", "other", "european-public-limited-liability-company-se",
                           "uk-establishment", "scottish-partnership", "charitable-incorporated-organisation",
                           "scottish-charitable-incorporated-organisation", "further-education-or-sixth-form-college-corporation",
                           "registered-overseas-entity"]

    valid_company_subtypes = ["community-interest-company", "private-fund-limited-partnership"]

    # Validate company status values
    for status in company_status:
        if status not in valid_company_status:
            raise ValueError(f"Invalid company status: {status}. Valid options are: {valid_company_status}.")


    headers = {"Authorization": f"Basic {api_key}"}

    params = {
        "company_name_includes": name_includes,
        "company_name_excludes": name_excludes,
        "company_status": ",".join(company_status),  # Convert list to comma-separated string
        "sic_codes": ",".join(sic_codes)  # Convert list to comma-separated string
    }

    url = ch_base_url + "advanced-search/companies"

    r = session.get(url, headers=headers, params=params)
    if r.status_code == 200:
        return r.json()
    else:
        print(f"Call {params} failed to {url} with code {r.status_code} and headers {r.headers}")
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

    if persons_sig == None:
        return []

    active_sig_persons = []
    
    # HERE NEEDS TO BE A CHECK FOR CEASED RATHER THAN USING ACTIVE

    for i in range(0, len(persons_sig['items'])):
        if not persons_sig['items'][i]['ceased']:
            active_sig_persons.append(persons_sig['items'][i])

    return active_sig_persons

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

def recusive_get_company_tree_from_sigs(company_name):
    """
    Recursively fetches the company tree of significant controllers (SIGs) for a given company name.

    Args:
        company_name (str): The name of the company for which the significant controllers' network is to be retrieved.

    Returns:
        list: A list of dictionaries, each representing an entity with significant control over the company or its subsidiaries.
    """

    search_result = search_ch(company_name)
    if not search_result:
        print(f"No search results found for term {company_name}")
        return []
    
    company_info = search_result['items'][0]
    company_number = company_info['company_number']
    company_name = company_info['title']

    sig_control_list = get_active_sig_persons_from_name(company_name)
    if not sig_control_list:
        print(f"No significant controllers found for {company_name}")
        return []

    entity_data = []
    visited_entities = set()

    def traverse_entities(entities, company_number, company_name):
        
        # for each in significant control
        for entity in entities:
            
            # Changed to using ceaased to determine if it should be added
            if not entity['ceased']:
                if entity['kind'] == 'corporate-entity-person-with-significant-control':
                    if entity['etag'] not in visited_entities:

                        visited_entities.add(entity['etag'])
                        entity_data.append({
                            'company_id': company_number,
                            'company_name': company_name,
                            'etag': entity['etag'],
                            'name': entity['name'],
                            'nature_of_control': entity['natures_of_control'],
                            'link': constuct_ch_link(company_number),
                            'kind': entity['kind'],
                            'notified_on' : entity['notified_on']
                        })

                        other_sig_control_list = get_active_sig_persons_from_name(entity['name'])

                        # Potentially add in some validation on if individual or company here

                        if other_sig_control_list:
                            other_company_info = search_ch(entity['name'])['items'][0]
                            traverse_entities(other_sig_control_list, other_company_info['company_number'], other_company_info['title'])
    
    traverse_entities(sig_control_list, company_number, company_name)
    
    return entity_data