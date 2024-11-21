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

# super basic cache for testing without pinging api
cache = {}


# Global list to store search history
search_history = []


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
                           accounts=data['accounts'], 
                           link=data.get('link', ''))  # Using get to handle some companies without linksaccounts
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
        # Get the data for the node
        node_data = {
            'data': {'id': node, 'label': graph.nodes[node].get('label', node), 'link': graph.nodes[node].get('link', ''),
                     'accounts' : graph.nodes[node].get('accounts', '')}
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

# tap nodes
#
@app.callback(
    Output('node-detail', 'children'),
    Output('node-detail', 'style'),
    [Input('cytoscape-network', 'tapNodeData')]
)
def display_node_data(node_data):
    if node_data:
        link = node_data.get('link', 'N/A')

        details = [
            html.H4("Company Details"),
            html.P(f"Name: {node_data.get('label')}"),
            html.P(f"ID: {node_data.get('id')}"),
            html.P([
                "Link: ",
                html.A(f"{link}", href=f'https://{link}', target="_blank")
            ]),
            html.P(f"Accounts: {node_data.get('accounts')}")
            # Add other details here
        ]
        return details, {'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px', 'display': 'block'}
    return "", {'display': 'none'}

# Callback to tap edges
@app.callback(
    Output('control-info', 'children'),
    Input('cytoscape-network', 'tapEdgeData')
)
def display_edge_info(edge_data):
    if edge_data:
        return f"Nature of Control: {edge_data['nature_of_control']}"
    return "Click on an edge to see the nature of control information."

# Searcxh history
@app.callback(
    Output('input-company-name', 'value'),
    [Input('search-history-dropdown', 'value')]
)
def select_from_history(selected_company):
    if selected_company:
        return selected_company
    return ""




'''
Most of this layout is just placeholder during dev
Lookup how to make this better
'''
app.layout = html.Div([
    html.H1("Interlocking Directorates Network"),
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
                style={'width': '100%', 'height': '500px'},
                elements=[],
                stylesheet=[
                    {'selector': 'node', 'style': {'label': 'data(label)', 'color': 'black'}},
                    {'selector': '.company', 'style': {'background-color': 'red'}},
                    {'selector': '.entity', 'style': {'background-color': 'green'}},
                    {'selector': '.search-company', 'style': {'background-color': 'blue'}},
                    {'selector': 'edge', 'style': {'line-color': '#ccc'}},
                    {'selector': '.highlighted', 'style': {'background-color': '#FFD700', 'line-color': '#FFD700', 'width': 3}},
                    {'selector': '.ownership-of-shares', 'style': {'line-color': 'red'}},
                    {'selector': '.voting-rights', 'style': {'line-color': 'blue'}},
                    {'selector': '.right-to-appoint-remove-directors', 'style': {'line-color': 'green'}}
                ]
            )
        ]
    ),
    html.Div(id='message', style={'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px', 'display': 'none'}),
    html.Div(id='dummy-output', style={'display': 'none'}),
    html.Div([
        html.H3("Search History"),
        dcc.Dropdown(id='search-history-dropdown', options=[], placeholder="Select a past search")
    ], style={'margin-top': '20px'}),
    html.Div(id='node-detail', style={'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px', 'display': 'none'})
])

@app.callback(
    Output('cytoscape-network', 'elements'),
    Output('message', 'children'),
    Output('message', 'style'),
    Output('search-history-dropdown', 'options'),
    [Input('submit-button', 'n_clicks')],
    [State('input-company-name', 'value')]
)
def update_network(n_clicks, company_name):
    if n_clicks > 0 and company_name:
        print(f"Search value: {company_name}")
        
        # simple cache for now
        if company_name in cache:
            directors_data = cache[company_name]
            print(f"Cache hit for company: {company_name}")
        else:
            directors_data = scraper.recusive_get_company_tree_from_sigs(company_name)
            if directors_data:
                cache[company_name] = directors_data
                print(f"Cache store for company: {company_name}")
                
        if not directors_data:
            return [], f"No results found for company: {company_name}", {'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px', 'display': 'block'}, search_history
        
        network = create_interlock_network(directors_data)
        elements = create_cytoscape_elements(network, company_name)

        # Update search history
        if company_name not in search_history:
            search_history.append(company_name)
        
        # Create options for the dropdown
        options = [{'label': name, 'value': name} for name in search_history]

        return elements, "", {'display': 'none'}, options
    
    return [], "", {'display': 'none'}, search_history


if __name__ == '__main__':
    app.run_server(debug=True)
