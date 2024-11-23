import requests, re, os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

###
### New Stuff that could be added
###
# Lookup old names

api_key = os.getenv('API_KEY')
ch_base_url = 'https://api.company-information.service.gov.uk/'

session = requests.Session()
session.auth= (api_key, "")

# changed all calls to use this, easier to debug and opti
def make_api_call(endpoint, params=None, method="GET"):

    headers = {"Authorization": f"Basic {api_key}"}
    
    url = ch_base_url + endpoint

    try:
        if method == "GET":
            r = session.get(url, headers=headers, params=params)
        else:
            raise NotImplementedError(f"HTTP method {method} not supported.")

        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:
            raise ValueError(f"Resource not found: {url}")
        else:
            raise RuntimeError(f"API call failed with status {r.status_code}: {r.text}")
    except requests.RequestException as e:
        raise RuntimeError(f"Request failed: {e}")



def search_ch(name):
    """
    Searches for a company on the Companies House API using the provided company name.

    Args:
        name (str): The name of the company to search for.

    Returns:
        dict: A dictionary containing the search results if the request is successful.
        If the request fails, it returns None and prints an error message.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Company name must be a non-empty string.")
    
    return make_api_call('search/companies', params={"q": name})

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

    params = {"items_per_page" : '10',
              "start_index" : '0',
              "register_view": 'false'}
    
    return make_api_call(f"{company_link}/persons-with-significant-control", params=params)

def get_entity_information(self_link):
    '''
    Returns info on corporate entities

    Input: self link from active_sig_entities
    '''
    return make_api_call(self_link)

def get_filling_history(company_number):
    return make_api_call(f"company/{company_number}/filing-history'")

def get_company_profile(company_number):
    return make_api_call(f"company/{company_number}")

def get_active_sig_persons_from_name(company_name):

    res = search_ch(company_name)

    company_link = res['items'][0]['links']['self']

    persons_sig = get_persons_with_control_info(company_link)

    if persons_sig == None:
        return []

    active_sig_persons = []

    for i in range(0, len(persons_sig['items'])):
        if not persons_sig['items'][i]['ceased']:
            active_sig_persons.append(persons_sig['items'][i])

    return active_sig_persons


def constuct_ch_link(company_number):
    new_url = f"find-and-update.company-information.service.gov.uk/company/{company_number}/"
    return new_url

def rename_control_outputs(nature_of_controls):
    '''
    This needs vastly improving for all nature of control
    '''
    # Define the regex pattern to match text and numbers
    pattern = re.compile(r'(\w+(?:-\w+)+)-(\d+)-to-(\d+)-percent')

    # Define the function to replace matched patterns
    def replace_func(match):
        text = match.group(1).replace('-', ' ')
        lower_bound = match.group(2)
        upper_bound = match.group(3)
        if text == 'ownership of shares':
            return f"Ownership of shares: >{lower_bound}%"
        elif text == 'voting rights':
            return f"Voting rights: >{lower_bound}%"
        return text

    # Loop through the list and apply the regex replacement
    for i, item in enumerate(nature_of_controls):
        nature_of_controls[i] = pattern.sub(replace_func, item)

    return nature_of_controls


def get_company_tree(company_name):
    """
    Recursively fetches the company tree of significant controllers (SIGs) for a given company name.

    Args:
        company_name (str): The name of the company for which the significant controllers' network is to be retrieved.

    Returns:
        list: A list of dictionaries, each representing an entity with significant control over the company or its subsidiaries.
    """

    def fetch_significant_controllers(company_name):
        """Fetch significant controllers for a company by name."""
        search_result = search_ch(company_name)
        if not search_result or not search_result.get('items'):
            print(f"No search results found for term {company_name}")
            return None, None

        company_info = search_result['items'][0]
        significant_controllers = get_active_sig_persons_from_name(company_info['title'])
        return company_info, significant_controllers
    
    def process_entity(entity, company_number, company_name):
        """Process and structure information for a single significant control entity."""

        company_profile = get_company_profile(company_number)
        accounts = company_profile.get('accounts', {}) if company_profile else {}
        return {
            'company_id': company_number,
            'company_name': company_name,
            'etag': entity.get('etag'),
            'name': entity.get('name'),
            'nature_of_control': rename_control_outputs(entity.get('natures_of_control', [])),
            'link': constuct_ch_link(company_number),
            'kind': entity.get('kind'),
            'notified_on': entity.get('notified_on'),
            'locality': entity.get('address', {}).get('locality'),
            'accounts': accounts
        }
    
    def traverse_entities(entities, company_number, company_name):
        """Traverse through entities recursively to build the tree."""

        for entity in entities:
            if not entity.get('ceased') and entity['kind'] == 'corporate-entity-person-with-significant-control':
                if entity['etag'] not in visited_entities:
                    visited_entities.add(entity['etag'])
                    structured_data = process_entity(entity, company_number, company_name)
                    entity_data.append(structured_data)

                    # Fetch the next level of significant controllers
                    other_company_name = entity['name']
                    other_company_info, other_controllers = fetch_significant_controllers(other_company_name)

                    if other_controllers and other_company_info:
                        traverse_entities(other_controllers, other_company_info['company_number'], other_company_info['title'])
    
    
    # Initial fetch for the root company
    root_company_info, root_controllers = fetch_significant_controllers(company_name)

    if not root_controllers:
        print(f"No significant controllers found for {company_name}")
        return [root_company_info] if root_company_info else []

    entity_data = []
    visited_entities = set()

    # Traverse
    traverse_entities(root_controllers, root_company_info['company_number'], root_company_info['title'])

    return entity_data
