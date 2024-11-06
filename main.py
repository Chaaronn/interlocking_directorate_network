import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_cytoscape as cyto
import networkx as nx
import scraper
import re
import webbrowser

app = dash.Dash(__name__)
app.title = "Interlocking Directorates Network"


def normalise_company_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()


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
                               type='company', 
                               link=data.get('link', ''))  # Get link. Using get to handle some companies without links
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



def create_cytoscape_elements(graph, search_company):

    # Empty list to hold all the nodes in the graph
    elements = []

    # normalise the name (comp house is caps by default)
    search_company_normalised = normalise_company_name(search_company)

    # NODES
    for node in graph.nodes():

        # Get the data from the node
        node_data = {
            'data': {'id': node, 'label': graph.nodes[node].get('label', node), 'link': graph.nodes[node].get('link', '')}
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

# opening links
### needs to change from opening a new browser
@app.callback(
    Output('dummy-output', 'children'),  # Dummy output to avoid errors
    [Input('cytoscape-network', 'tapNodeData')]
)
def open_link(node_data):
    if node_data:
        # Get link from the clicked node
        link = node_data.get('link')  
        if link:
            webbrowser.open(link)
    return ""


# Callback to display edge info
@app.callback(
    Output('control-info', 'children'),
    Input('cytoscape-network', 'tapEdgeData')
)
def display_edge_info(edge_data):
    if edge_data:
        return f"Nature of Control: {edge_data['nature_of_control']}"
    return "Click on an edge to see the nature of control information."



'''
Most of this layout is just placeholder during dev
Lookup how to make this better
'''
app.layout = html.Div([
    html.H1("Interlocking Directorates Network"),   # Needs a better name lol
    html.Div([
        dcc.Input(id='input-company-name', type='text', placeholder='Enter Company Name'),
        html.Button(id='submit-button', n_clicks=0, children='Submit'),
    ], className="input-container"),
    html.Div(id='control-info', style={'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px'}),
    dcc.Loading(
        id='loading',
        type="default",
        children=[
            cyto.Cytoscape(
                id='cytoscape-network',
                layout={'name': 'cose'},
                style={'width': '100%', 'height': '800px'},
                elements=[],
                stylesheet=[
                    {'selector': 'node', 'style': {'label': 'data(label)', 'color': 'black'}},
                    {'selector': '.company', 'style': {'background-color': 'red'}},
                    {'selector': '.entity', 'style': {'background-color': 'green'}},
                    {'selector': '.search-company', 'style': {'background-color': 'blue'}},  # Original company
                    {'selector': 'edge', 'style': {'line-color': '#ccc'}},
                    {'selector': '.highlighted', 'style': {'background-color': '#FFD700', 'line-color': '#FFD700', 'width': 3}},

                    # These aren't really working
                    {'selector': '.ownership-of-shares', 'style': {'line-color': 'red'}},
                    {'selector': '.voting-rights', 'style': {'line-color': 'blue'}},
                    {'selector': '.right-to-appoint-remove-directors', 'style': {'line-color': 'green'}},
                    # Need to add other styles for different natures of control here
                ]
            )
        ]
    ),
    html.Div(id='dummy-output', style={'display': 'none'}),
])

# Callback for submit button
@app.callback(
    Output('cytoscape-network', 'elements'),
    [Input('submit-button', 'n_clicks')],
    [State('input-company-name', 'value')]
)
def update_network(n_clicks, company_name):
    # Make sure a name has been typed
    if n_clicks > 0 and company_name:
        print(f"Search value: {company_name}")
        directors_data = scraper.recusive_get_company_tree_from_sigs(company_name)
        print(f"Data found: {directors_data}")
        network = create_interlock_network(directors_data)
        elements = create_cytoscape_elements(network, company_name)
        return elements
    return []

if __name__ == '__main__':
    app.run_server(debug=True)
