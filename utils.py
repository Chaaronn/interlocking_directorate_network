import re, logging
import networkx as nx
from scraper import get_filling_history

# Helper to normalise names
def normalise_company_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

# Create the network
def create_interlock_network(entity_data):
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
    Calculate basic metrics for the graph.
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