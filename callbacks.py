from dash.dependencies import Input, Output, State
from dash import html, dcc
import utils, scraper
import logging


# Cache and search history
cache = {}
search_history = []



# Main search function
def register_callbacks(app):
    @app.callback(
    Output('cytoscape-network', 'elements'),
    Output('message', 'children'),
    Output('message', 'style'),
    Output('search-history-dropdown', 'options'),
    Output('collapse-analytics', 'children'),
    [Input('submit-button', 'n_clicks')],
    [State('input-company-name', 'value')]
    )
    def update_network(n_clicks, company_name):
        if n_clicks > 0 and company_name:
            logging.info(f"Search value: {company_name}")
            
            # get the data
            directors_data = utils.process_network_data(company_name, scraper.recusive_get_company_tree_from_sigs, cache)
                    
            if not directors_data:
                return [], f"No results found for company: {company_name}", {'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px', 'display': 'block'}, search_history
            
            network = utils.create_interlock_network(directors_data)
            elements = utils.create_cytoscape_elements(network, company_name)

            # Calculate analytics
            metrics = utils.calculate_network_metrics(network)
            analytics = [
                html.H3("Network Analytics"),
                html.P(f"Total Companies: {metrics['total_companies']}"),
                html.P(f"Total Edges: {metrics['total_edges']}")
            ]


            # Update search history
            if company_name not in search_history:
                search_history.append(company_name)
            
            # Create options for the dropdown
            options = [{'label': name, 'value': name} for name in search_history]

            return elements, "", {'display': 'none'}, options, analytics
        
        return [], "", {'display': 'none'}, search_history, ""
    
    # Searcxh history
    @app.callback(
        Output('input-company-name', 'value'),
        [Input('search-history-dropdown', 'value')]
    )
    def select_from_history(selected_company):
        if selected_company:
            return selected_company
        return ""
    
        # Analytics
    @app.callback(
    Output('collapse-analytics', 'is_open'),
    [Input('analytics-toggle', 'n_clicks')],
    [State('collapse-analytics', 'is_open')]
    )
    def toggle_analytics(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return is_open




# Tap callbacks
def register_cytoscape_callbacks(app):
    # Tap node data
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
                html.P(f"Period Ends: {node_data.get('period_end')}")
                # Add other details here
            ]
            return details, {'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px', 'display': 'block'}
        return "", {'display': 'none'}

    # tap Edge data
    @app.callback(
        Output('control-info', 'children'),
        Input('cytoscape-network', 'tapEdgeData')
    )
    def display_edge_info(edge_data):
        if edge_data:
            return f"Nature of Control: {edge_data['nature_of_control']}"
        return "Click on an edge to see the nature of control information."
    




'''
# Rest button
@app.callback(
    Output('cytoscape-network', 'zoom'),
    Output('cytoscape-network', 'elements'),
    Output('cytoscape-network', 'layout'),
    [Input('reset-button', 'n_clicks')],
    [State('cytoscape-network', 'elements')]
)
def reset_view(n_clicks, elements, layout):
    if n_clicks > 0:
        return 1.0, elements, {'name': layout}
    return dash.no_update, dash.no_update, dash.no_update
'''


'''
Most of this layout is just placeholder during dev
Lookup how to make this better
'''