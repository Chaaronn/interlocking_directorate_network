import requests, re, os, tempfile
import logging, time
from collections import deque
import base64
import pandas as pd

logging.basicConfig(level=logging.INFO)

###
### New Stuff that could be added
###
# Lookup old names

api_key = os.getenv('API_KEY')
ch_base_url = 'https://api.company-information.service.gov.uk/'

session = requests.Session()
session.auth= (api_key, "")

# Global list to store request timestamps
request_timestamps = deque()

# Define the rate limit and time window
MAX_REQUESTS = 600  # Maximum number of requests
TIME_WINDOW = 5 * 60  # 5 minutes (in seconds)


# changed all calls to use this and below, easier to debug and opti
def make_api_call(endpoint, params=None, method="GET"):
    """
    Makes an API call to the specified endpoint with the given parameters and HTTP method.

    Args:
        endpoint (str): The API endpoint to make the request to.
        params (dict, optional): A dictionary of parameters to include in the request.
        method (str, optional): The HTTP method to use for the request (default is "GET").

    Returns:
        dict: The JSON response from the API if the request is successful.

    Raises:
        RuntimeError: If the API call fails or returns a non-200 status code.
        ValueError: If the resource is not found (404).
    """

    headers = {"Authorization": f"Basic {api_key}"}
    
    url = ch_base_url + endpoint

    try:
        if method == "GET":
            r = session.get(url, headers=headers, params=params, timeout=30)
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

# added rate limiting automatically
def rate_limited_make_api_call(endpoint, params=None, method="GET"):
    """
    Makes an API call while adhering to rate limiting (600 requests per 5 minutes).

    Args:
        endpoint (str): The API endpoint to make the request to.
        params (dict, optional): A dictionary of parameters to include in the request.
        method (str, optional): The HTTP method to use for the request (default is "GET").

    Returns:
        dict: The JSON response from the API if the request is successful.
    """
    # Check if exceeded the rate limit
    current_time = time.time()
    
    # Remove old timestamps that are outside the window
    while request_timestamps and current_time - request_timestamps[0] > TIME_WINDOW:
        request_timestamps.popleft()
    
    if len(request_timestamps) >= MAX_REQUESTS:
        # Wait until next request
        sleep_time = TIME_WINDOW - (current_time - request_timestamps[0])
        logging.info(f"Rate limit exceeded, sleeping for {sleep_time:.2f} seconds.")
        time.sleep(sleep_time)

    # Add the current time to the request queue
    request_timestamps.append(current_time)

    # Now make the API call
    return make_api_call(endpoint, params=params, method=method)

def search_ch(name):
    """
    Searches for a company on the Companies House API using the provided company name.

    Args:
        name (str): The name of the company to search for.

    Returns:
        dict: A dictionary containing the search results if the request is successful.
        If the request fails, it returns None and prints an error message.
    
    Raises:
        ValueError: If the company name is not a non-empty string.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Company name must be a non-empty string.")
    
    return rate_limited_make_api_call('search/companies', params={"q": name})

def adv_search_ch(name_includes, name_excludes='', company_status='', company_subtype='', company_type='', 
                  dissolved_from='', dissolved_to='', incorporated_from='', incorporated_to='', location='',
                    sic_codes=''):
    """
    Performs an advanced search for a company on the Companies House API using various company details.

    Args:
        name_includes (str): The part of the company name to search for.
        name_excludes (str): The part of the company name to exclude from the search.
        company_status (list or str): The company status filter for the search.
        company_subtype (str, optional): The company subtype filter.
        company_type (str, optional): The company type filter.
        dissolved_from (str, optional): The date filter for when the company was dissolved.
        dissolved_to (str, optional): The date filter for when the company was dissolved.
        incorporated_from (str, optional): The date filter for when the company was incorporated.
        incorporated_to (str, optional): The date filter for when the company was incorporated.
        location (str, optional): The location filter for the search.
        sic_codes (list or str, optional): The SIC code filter for the search.

    Returns:
        dict: A dictionary containing the search results if the request is successful.

    Raises:
        ValueError: If invalid input types are provided for the arguments.
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

    params = {
        "company_name_includes": name_includes,
        "company_name_excludes": name_excludes,
        "company_status": ",".join(company_status),  # Convert list to comma-separated string
        "sic_codes": ",".join(sic_codes)  # Convert list to comma-separated string
    }

    return rate_limited_make_api_call("advanced-search/companies", params={"q" : params})

def get_persons_with_control_info(company_link):
    """
    Retrieves information about persons with significant control (PSC) for a company using its link.

    Args:
        company_link (str): The link to the company's details in the Companies House API.

    Returns:
        dict: A dictionary containing information about persons with significant control (PSC).
    """

    params = {"items_per_page" : '10',
              "start_index" : '0',
              "register_view": 'false'}
    
    return rate_limited_make_api_call(f"{company_link}/persons-with-significant-control", params=params)

def get_entity_information(self_link):
    """
    Retrieves information about a corporate entity using its self link.

    Args:
        self_link (str): The self link of the corporate entity.

    Returns:
        dict: A dictionary containing the entity information.
    """
    return rate_limited_make_api_call(self_link)

def get_filling_history(company_number):
    """
    Retrieves the filing history of a company using its company number.

    Args:
        company_number (str): The company number of the company.

    Returns:
        dict: A dictionary containing the filing history of the company.
    """
    return rate_limited_make_api_call(f"company/{company_number}/filing-history")

def get_company_profile(company_number):
    """
    Retrieves the company profile of a company using its company number.

    Args:
        company_number (str): The company number of the company.

    Returns:
        dict: A dictionary containing the profile information of the company.
    """
    return rate_limited_make_api_call(f"company/{company_number}")

def get_company_registers(company_number):
    return rate_limited_make_api_call(f"company/{company_number}/registers")

def get_document(document_metadata, method='GET'):
    """
    Retrieves and downloads a document from the Companies House API using document metadata.

    Args:
        document_metadata (str): The metadata of the document to be retrieved.
        method (str, optional): The HTTP method to use for the request (default is "GET").

    Returns:
        str: The file path where the document was saved.

    Raises:
        RuntimeError: If the request for the document fails.
        ValueError: If the document retrieval fails.
    """
    
    # This needs a rework of the make_api_call and rate_limited but this is fine for testing
    # Also, lookup rate limit for this
    encoded_key = base64.b64encode(api_key.encode('utf-8')).decode('utf-8')
    
    headers = {"Authorization": f"Basic {encoded_key}"}
    
    url = f"{document_metadata}/content"

    # always initialise
    temp_dir = tempfile.gettempdir()
    file_path = ''

    try:
        #logging.info(f"Requesting document {document_metadata} from URL: {url}")
        r = requests.get(url, headers=headers, timeout=30)
        
        # handle redirects, as this will send to AWS I think?

        if r.status_code == 302:  # Redirect response
            redirected_url = r.headers.get("Location")  # Get the redirect location
            logging.info(f"Redirected to {redirected_url}")
            # Follow the redirect manually and include the Auth header
            r = requests.get(redirected_url, headers=headers, )

        # Check the response status
        if r.status_code == 200:
            logging.info(f"Document {document_metadata} exists. Starting download.")
            
            # Save the document locally
            file_path = os.path.join(temp_dir, f"document.pdf")
            with open(file_path, "wb") as f:
                f.write(r.content)
                logging.info(f"Wrote document {document_metadata} to {file_path}")
            
            # Return the path to serve the file later
            return file_path
        else:
            raise ValueError(f"Failed to download document: HTTP {r.status_code}")
    
    except requests.RequestException as e:
        # Handle general request exceptions
        logging.error(f"Request for document {document_metadata} failed: {e}")
        raise RuntimeError(f"Request failed: {e}")

def get_active_sig_persons_from_name(company_name):
    """
    Retrieves a list of active persons with significant control (PSC) for a company using the company name.

    Args:
        company_name (str): The name of the company to search for.

    Returns:
        list: A list of active persons with significant control (PSC) for the company.
    """

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
    """
    Constructs the Companies House link for a company using its company number.

    Args:
        company_number (str): The company number of the company.

    Returns:
        str: The Companies House link for the company.
    """

    new_url = f"find-and-update.company-information.service.gov.uk/company/{company_number}/"
    return new_url

def get_addresses(csv_path):
    """
    Reads a list of companies in a CSV, and returns their addresses in the same file
    """
    
    df = pd.read_csv(csv_path, dtype={
    'company_number': str,
    'company_name': str,
    'full_address': str,
    'address_line_1': str,
    'address_line_2': str,
    'country': str,
    'postal_code': str,
    'locality': str,
    'region': str,
    'previous_name' : str
    })

    # needed as csv is full and doesnt contain full address column
    if 'full_address' not in df.columns:
        df['full_address'] = ''  

    for index, row in df.iterrows():
        company_number = row["company_number"]
        company_number = str(company_number).strip()

        try:
            data = get_company_profile(company_number)
            address_data = data['registered_office_address']
        except ValueError as e:
            logging.warning(f"Company {company_number} not found: {e}")
            data = []
            address_data = []
            continue
        except Exception as e:
            logging.error(f"Unexpected error for {company_number}: {e}")
            continue

        


        # Store results in the DataFrame
        df.at[index, 'company_name'] = data.get('company_name', '')

        # Should concat these into one line with commas
        # and change csv to jsut "address"
        full_address = ', '.join(filter(None, [
            address_data.get('address_line_1', ''),
            address_data.get('address_line_2', ''),
            address_data.get('locality', ''),
            address_data.get('region', ''),
            address_data.get('postal_code', ''),
            address_data.get('country', '')
        ]))
        
        df.at[index, 'full_address'] = full_address
        df.at[index, 'address_line_1'] = address_data.get('address_line_1', '')
        df.at[index, 'address_line_2'] = address_data.get('address_line_2', '')
        df.at[index, 'country'] = address_data.get('country', '')
        df.at[index, 'postal_code'] = address_data.get('postal_code', '')
        df.at[index, 'locality'] = address_data.get('locality', '')
        df.at[index, 'region'] = address_data.get('region', '')


        if 'previous_company_names' in data and data['previous_company_names']:
            df.at[index, 'previous_name'] = data['previous_company_names'][0].get('name', '')
        else:
            df.at[index, 'previous_name'] = ''
    
    df.to_csv(csv_path, index=False)

get_addresses("companies.csv")
print("complete")

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

        if not company_info:
            logging.error(f"No info found for {company_name}")

        significant_controllers = get_active_sig_persons_from_name(company_info['title'])
        if not significant_controllers:
            logging.error(f"No significant controllers found for {company_name}")
            significant_controllers = {}

        return company_info, significant_controllers
    
    def process_entity(entity, company_number, company_name):
        """Process and structure information for a single significant control entity."""

        company_profile = get_company_profile(company_number)
        if not company_profile:
            logging.error(f"No company profile found for {company_name}")

        filling_history = get_filling_history(company_number) # maybe need to add handling of no history
        if not filling_history:
            logging.info(f"Filing history not found for: {company_name}")

        accounts = company_profile.get('accounts', {}) if company_profile else {}
        previous_names = company_profile.get("previous_company_names", {}) if company_profile else {}

        return {
            'company_id': company_number,
            'company_name': company_name,
            'etag': entity.get('etag', f"default-{company_number}"),
            'name': entity.get('name', 'No name found'),
            'nature_of_control': entity.get('natures_of_control', []),
            'link': constuct_ch_link(company_number),
            'kind': entity.get('kind', 'No kind found'),
            'notified_on': entity.get('notified_on', 'No data found'),
            'locality': entity.get('address', {}).get('locality', 'No locality found'),
            'accounts': accounts,
            'previous_names' : previous_names,
            'filing_history' : filling_history
        }
    
    def traverse_entities(entities, root_company_info, entity_data=None):
        """Traverse through entities recursively to build the tree."""

        if entity_data is None:
            entity_data = []

        logging.info(f"Traversing entities for {root_company_info['title']}")

        for entity in entities:
            logging.info(f"Processing entity: {entity.get('name', 'Unknown')} of kind: {entity.get('kind', 'Unknown')}")

            if not entity.get('ceased') and entity['kind'] == 'corporate-entity-person-with-significant-control': # As we only care about companies, not individuals
                
                logging.info(f"Entity {entity.get('name', 'Unknown')} added as kind corporate-entity-person-with-significant-control")
                
                if entity['etag'] not in visited_entities:
                    visited_entities.add(entity['etag'])
                    structured_data = process_entity(entity, root_company_info['company_number'], root_company_info['title'])
                    entity_data.append(structured_data)

                    for data in entity_data:
                        logging.info(f"{data['name']} added to list.")

                    # Fetch the next level of significant controllers
                    other_company_name = entity['name']
                    other_company_info, other_controllers = fetch_significant_controllers(other_company_name)

                    if other_company_info:
                        if other_controllers:
                            traverse_entities(other_controllers, other_company_info, entity_data)
                        else: 
                            structured_data = process_entity(other_company_info, other_company_info['company_number'], other_company_name)
                            entity_data.append(structured_data)
                    else:
                        logging.warning(f"Entity {entity['name']} not being traversed due to no controllers or info")
            
            # Handling non-UK owners
            elif entity['address']['country'] == 'Not specified' or '':
                # This is causing the last node to not be displayed for some reason
                logging.info(f"Significant controllers for {root_company_info['title']} are not based in UK")

                if entity['etag'] not in visited_entities:


                    visited_entities.add(entity['etag'])

                    entity_data.append({
                    'company_id': entity.get('etag', 'Unknown'),     # Must use etag as no number on CH
                    'company_name': entity.get('name', 'Unknown'),
                    'etag': entity.get('etag', 'Unknown'),
                    'nature_of_control': entity['natures_of_control'],
                    'link': constuct_ch_link(entity['links']['self']),  # This is giving wrong links
                    'kind': entity.get('kind', 'Unknown'),
                    'notified_on': entity.get('notified_on', 'No data found'),
                    'locality': entity['address']['locality'],
                    'accounts': {'last_accounts' : {'period_end_on' : 'NA'}},   # We dont have this info from CH
                    'previous_names': [],   # We dont have this
                    'filing_history' : [] # We al;so dont have
                    })

                    other_company_info, other_controllers = fetch_significant_controllers(entity['name'])
                    if other_controllers and other_company_info:
                        traverse_entities(other_controllers,other_company_info)

            # Handling non-companies             
            else:
                logging.info(f"Significant controllers for {root_company_info['title']} are non-company")
                #
                entity_data.append({
                'company_id': root_company_info.get('company_number', 'Unknown'),
                'company_name': root_company_info.get('title', 'Unknown'),
                'etag': root_company_info.get('etag', 'Unknown'),
                'nature_of_control': [],
                'link': constuct_ch_link(root_company_info.get('company_number', 'Unknown')),
                'kind': 'root',
                'notified_on': 'N/A',
                'locality': root_company_info.get('address_snippet', 'Unknown'),
                'accounts': {'last_accounts' : {'period_end_on' : 'NA'}},
                'previous_names': root_company_info.get('previous_company_names', []),
                'filing_history' : get_filling_history(root_company_info.get('company_number', 'Unknown'))
                })

        return entity_data
    
    
    # Initial fetch for the root company
    root_company_info, root_controllers = fetch_significant_controllers(company_name)

    # Handle cases where no sig controlers exist by returning base info
    
    if not root_controllers:
        logging.info(f"No significant controllers found for {company_name}")
        return [{
        'company_id': root_company_info.get('company_number', 'Unknown'),
        'company_name': root_company_info.get('title', company_name),
        'etag': root_company_info.get('etag', 'Unknown'),
        'nature_of_control': [],
        'link': constuct_ch_link(root_company_info.get('company_number', 'Unknown')),
        'kind': 'root',
        'notified_on': 'N/A',
        'locality': root_company_info.get('address_snippet', 'Unknown'),
        'accounts': {'last_accounts' : {'period_end_on' : 'NA'}},
        'previous_names': root_company_info.get('previous_company_names', []),
        'filing_history' : get_filling_history(root_company_info.get('company_number', 'Unknown'))
        }] if root_company_info else []

    visited_entities = set()

    # Traverse
    entity_data = traverse_entities(root_controllers, root_company_info)

    for entity in entity_data:
        logging.info(f"Entity: {entity['company_name']} found in scraper.")

    return entity_data