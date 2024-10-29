import dash
from dash import html, dcc
from dash.dependencies import Input, Output, State
import dash_cytoscape as cyto
import networkx as nx
from datetime import datetime
import scraper
import re

app = dash.Dash(__name__)
app.title = "Interlocking Directorates Network"


def normalise_company_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

# recursive func test
def create_interlock_network(entity_data, start, end, company_name):
    G = nx.Graph()
    top_company_node = None
    last_entity_node = None
    visited_nodes = set()

    for data in entity_data:
        if isinstance(data, dict) and 'start_date' in data:
            if data['start_date'].year <= end and data['end_date'].year >= start:
                company_node = f"company_{data['company_id']}"
                entity_node = f"entity_{data['etag']}"

                if data['company_name'] == company_name:
                    top_company_node = company_node

                if company_node not in visited_nodes:
                    G.add_node(company_node, bipartite=0, label=data['company_name'], type='company')
                    visited_nodes.add(company_node)
                
                if entity_node not in visited_nodes:
                    G.add_node(entity_node, bipartite=1, label=data['name'], type='entity')
                    visited_nodes.add(entity_node)

                G.add_edge(company_node, entity_node, nature_of_control=data['nature_of_control'])

                if last_entity_node:
                    G.add_edge(last_entity_node, entity_node, nature_of_control=data['nature_of_control'])
                
                last_entity_node = entity_node
                
    if top_company_node:
        G.nodes[top_company_node]['color'] = 'blue'
            
    return G



def create_cytoscape_elements(graph, search_company):
    elements = []
    search_company_normalised = normalise_company_name(search_company)
    for node in graph.nodes():
        node_data = {
            'data': {'id': node, 'label': graph.nodes[node].get('label', node)}
        }
        node_classes = ['company' if graph.nodes[node].get('type') == 'company' else 'entity']
        node_label_normalised = normalise_company_name(graph.nodes[node].get('label', node))
        if node_label_normalised == search_company_normalised:
            node_classes.append('search-company')
        node_data['classes'] = ' '.join(node_classes)
        elements.append(node_data)
    
    for edge in graph.edges(data=True):
        elements.append({
            'data': {
                'source': edge[0],
                'target': edge[1],
                'nature_of_control': edge[2].get('nature_of_control', '')
            }
        })
    
    return elements

@app.callback(
    Output('control-info', 'children'),
    [Input('cytoscape-network', 'tapEdgeData')]
)
def display_edge_info(edge_data):
    if edge_data:
        return f"Nature of Control: {edge_data['nature_of_control']}"
    return "Click on an edge to see the nature of control information."


app.layout = html.Div([
    html.H1("Interlocking Directorates Network"),
    html.Div([
        dcc.Input(id='input-company-name', type='text', placeholder='Enter Company Name'),
        dcc.Input(id='input-start-year', type='number', placeholder='Start Year', value=1900),
        dcc.Input(id='input-end-year', type='number', placeholder='End Year', value=datetime.now().year),
        html.Button(id='submit-button', n_clicks=0, children='Submit'),
    ]),
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
            {'selector': '.highlighted', 'style': {'background-color': '#FFD700', 'line-color': '#FFD700', 'width': 3}}
        ]
    ),
    html.Div(id='control-info')
])


@app.callback(
    Output('cytoscape-network', 'elements'),
    [Input('submit-button', 'n_clicks')],
    [State('input-company-name', 'value'),
     State('input-start-year', 'value'),
     State('input-end-year', 'value')]
)
def update_network(n_clicks, company_name, start_year, end_year):
    if n_clicks > 0 and company_name:
        directors_data = scraper.recusive_get_company_tree_from_sigs(company_name, start_year, end_year)
        network = create_interlock_network(directors_data, start_year, end_year, company_name)
        elements = create_cytoscape_elements(network, company_name)
        return elements
    return []


if __name__ == '__main__':
    app.run_server(debug=True)
