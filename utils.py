import re, logging, yaml
import networkx as nx
from scraper import get_filling_history

# Helper to normalise names
def normalise_company_name(name):
    """
    Normalizes the company name by removing non-alphanumeric characters and converting to lowercase.

    Inputs:
        name: The company name to normalize.

    Outputs:
        A normalized version of the company name in lowercase with non-alphanumeric characters removed.
    """
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def clean_yaml_description(description):
    """
    Cleans the description text by removing curly braces content and Markdown asterisks.

    Inputs:
        description: The description text to clean.

    Outputs:
        The cleaned description text.
    """

    cleaned_desc = re.sub(r'\{.*?\}', '', description)

    # Remove Markdown asterisks (**) if present
    cleaned_desc = cleaned_desc.replace("**", "")

    return cleaned_desc

# Helper to load any YAML files
def load_descriptions(filepath):
    """
    Loads YAML descriptions from the given file path.

    Inputs:
        filepath: The path to the YAML file to load.

    Outputs:
        descriptions: A dictionary containing the descriptions from the YAML file.
    """

    with open(filepath, 'r') as file:

        yaml_data = yaml.safe_load(file)
    
    if yaml_data:
        descriptions = yaml_data.get("description", {})
        return descriptions
    else:
        logging.error(f"Error in accessing YAML file {filepath}")

# Global variable to hold the parsed descriptions
DESCRIPTIONS_DICT = load_descriptions('yamls/filing_history_descriptions.yml')
NATURE_OF_CONTROL_DICT = load_descriptions('yamls/psc_descriptions.yml')

# Create the network
def create_interlock_network(entity_data):
    """
    Creates a network graph representing the relationships between companies and entities.

    Inputs:
        entity_data: A list of dictionaries containing company and entity information.

    Outputs:
        G: A NetworkX graph representing the interlock between companies and entities.
    """
    # Create the graph
    G = nx.Graph()
    # Set nodes for the initial company, and the last visited one
    top_company_node = None
    last_entity_node = None
    # Empty set of nodes that have been created
    visited_nodes = set()
    # Now we loop over the entity data to display all companies
    for data in entity_data:
        # Make sure there is a dict
        if isinstance(data, dict):
            # Seperation of companies and entities
            company_node = data['etag']
            entity_node = data['etag']
            
            # If the current is first, it is the top company
            if top_company_node:
                pass
            else:
                top_company_node = company_node

            # Both these conditions stop duplicate nodes
            if company_node not in visited_nodes:
                G.add_node(company_node, 
                           bipartite=0, 
                           label=data['company_name'],
                           number = data['company_id'],
                           type='company',
                           period_end=data['accounts']['last_accounts']['period_end_on'],
                           previous_names=data['previous_names'], 
                           link=data.get('link', ''))  # Using get to handle some companies without links
                visited_nodes.add(company_node)

            if entity_node not in visited_nodes:
                G.add_node(entity_node, 
                           bipartite=1, 
                           label=data['name'], 
                           type='entity', 
                           link=data.get('link', ''))
                visited_nodes.add(entity_node)

            # Set the last as the last
            if last_entity_node:
                G.add_edge(last_entity_node, entity_node, nature_of_control=data['nature_of_control'])
            last_entity_node = entity_node
    
    # Sets top company as blue        
    if top_company_node:
        G.nodes[top_company_node]['color'] = 'blue'
    return G

# Create the elements to fill the graph
def create_cytoscape_elements(graph, search_company):
    """
    Converts a NetworkX graph into Cytoscape elements for visualization, highlighting the search company.

    Inputs:
        graph: A NetworkX graph representing the interlock network.
        search_company: The name of the company to highlight in the graph.

    Outputs:
        elements: A list of dictionaries representing Cytoscape elements (nodes and edges).
    """

    # Empty list to hold all the nodes in the graph
    elements = []
    # normalise the name (comp house is caps by default)
    search_company_normalised = normalise_company_name(search_company)

    # NODES
    for node in graph.nodes():
        # Get the data for the node
        node_data = {
            'data': {'id': node, 'label': graph.nodes[node].get('label', node), 'number': graph.nodes[node].get('number', ''), 'link': graph.nodes[node].get('link', ''),
                     'period_end' : graph.nodes[node].get('period_end', ''), 'previous_names' : graph.nodes[node].get('previous_names','')}
        }
        # Set company/entity
        node_classes = ['company' if graph.nodes[node].get('type') == 'company' else 'entity']
        # Normalise the node info
        node_label_normalised = normalise_company_name(graph.nodes[node].get('label', node))
        # If the node matches the search, its the search
        if node_label_normalised == search_company_normalised:
            node_classes.append('search-company')
        node_data['classes'] = ' '.join(node_classes)
        elements.append(node_data)
    
    # EDGES
    for edge in graph.edges(data=True):
        # Get the nature of control info
        nature_of_control_list = edge[2].get('nature_of_control', [])
        # Its always a list so split it out
        edge_classes = ' '.join([noc.replace(' ', '-') for noc in nature_of_control_list])
        # Add in the data to the edge
        edge_data = {
            'data': {
                'source': edge[0],
                'target': edge[1],
                'nature_of_control': ', '.join(nature_of_control_list)
            },
            'classes': edge_classes
        }
        elements.append(edge_data)
    return elements

def process_network_data(company_name, scraper, cache):
    """
    Processes the network data for a given company, utilizing a cache for efficiency.

    Inputs:
        company_name: The name of the company to retrieve data for.
        scraper: The scraper function to fetch data for the company.
        cache: A dictionary storing previously fetched company data.

    Outputs:
        The company data (if available) either from the cache or fetched via the scraper.
    """

    # Simple cache
    if company_name in cache:
        logging.info(f"Cache hit for company: {company_name}")
        return cache[company_name]
        

    data = scraper(company_name)
    if data:
        logging.info(f"Cache store for company: {company_name}")
        cache[company_name] = data
    return data

def calculate_network_metrics(graph):
    """
    Calculates basic metrics for a given network graph, such as the total number of nodes, edges, and companies.

    Inputs:
        graph: A NetworkX graph representing the interlock network.

    Outputs:
        metrics: A dictionary containing the total nodes, edges, and companies in the network.
    """
    num_nodes = graph.number_of_nodes()
    num_edges = graph.number_of_edges()
    
    # Split nodes by type
    num_companies = sum(1 for _, data in graph.nodes(data=True) if data.get('type') == 'company')
    
    metrics = {
        'total_nodes': num_nodes,
        'total_edges': num_edges,
        'total_companies': num_companies
    }
    
    return metrics

def fetch_document_records(company_name, cache, company_number):
    """
    Fetches the filing history of a company, either from the cache or by calling an external scraper.

    Inputs:
        company_name: The name of the company to fetch the filing history for.
        cache: A dictionary storing previously fetched filing history data.
        company_number: The unique identifier of the company for external scraping.

    Outputs:
        filing_history: A list of filing history records for the company.
    """

    if company_name in cache:
        logging.info(f"Cache hit for {company_name}")
        hit = cache[company_name]
        filing_history = hit[0].get('filing_history', [])

        if not filing_history:
            logging.warning(f"No filing history found for {company_name}")
        return filing_history
    else:
        logging.info(f"No cache hit for {company_name} when fetching records")
        logging.info(f"Searching filiing for number {company_number}")
        filing_history = get_filling_history(company_number)

        return filing_history
    
def get_document_options(document_list):
    """
    Generates a list of document options for the dropdown, based on the document list.

    Inputs:
        document_list: A list of documents with metadata to generate options from.

    Outputs:
        options: A list of dictionaries containing the label and value for each document option.
    """
    
    options = []

    for doc in document_list:
        doc_code = doc.get("description", "") 
        doc_description = DESCRIPTIONS_DICT.get(doc_code, "Unknown Description")
        doc_date = doc.get("date", "N/A")  # Extract the document date

        # Format the display text for the dropdown
        display_text = f"{doc_description} ({doc_date})"
        options.append({"label": clean_yaml_description(display_text), "value": doc["links"]["document_metadata"]})

    return options