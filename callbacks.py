from dash.dependencies import Input, Output, State
from dash import html, no_update, dcc
import utils, scraper
import logging, os
from flask import send_file


# Cache and search history
cache = {}
search_history = []



# Main search function
def register_callbacks(app):
    """
    Registers callbacks for updating the network and interacting with the search history.

    Inputs:
        app: The Dash app instance.

    Outputs:
        None.
    """
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
        """
        Handles the search and updates the network visualization based on the company name input.

        Inputs:
            n_clicks: The number of times the submit button has been clicked.
            company_name: The name of the company entered by the user.

        Outputs:
            elements: A list of Cytoscape elements to display in the network.
            message: A message to show to the user (error or success).
            message_style: A style dictionary for the message box.
            options: The dropdown options for the search history.
            analytics: A list of analytics (network metrics like total companies and edges).
        """
        if n_clicks > 0 and company_name:
            logging.info(f"Search value: {company_name}")
            
            # get the first company here to store the name
            # VERY VERY VERY BAD to do this, but to test doc downloader
            initial_search = scraper.search_ch(company_name)
            first_result = initial_search['items'][0]['title']

            logging.info(f"First company: {first_result}")
            # get the data
            directors_data = utils.process_network_data(first_result, scraper.get_company_tree, cache)

            if not directors_data:
                # Provide all 5 outputs with appropriate placeholders
                # This fixes issues where directors_data is empty
                # This needs handling, as some display and others dont.
                return (
                    [initial_search],  # Empty elements for the network
                    f"No results found for company: {company_name}",  # Message
                    {'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px', 'display': 'block'},  # Message style
                    [{'label': name, 'value': name} for name in search_history],  # Dropdown options
                    []  # Empty analytics content
                )
            
            logging.info("Creating network.")
            network = utils.create_interlock_network(directors_data)
            logging.info("Network created. Populating graph.")
            for node, data in network.nodes(data=True):
                logging.info(f"found {node}, with data: {data}")
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
        
        return [], "", {'display': 'none'}, [{'label': name, 'value': name} for name in search_history], []
    
    # Searcxh history
    @app.callback(
        Output('input-company-name', 'value'),
        [Input('search-history-dropdown', 'value')]
    )
    def select_from_history(selected_company):
        """
        Handles the selection of a company from the search history dropdown.

        Inputs:
            selected_company: The company name selected from the dropdown.

        Outputs:
            The company name to be displayed in the search input.
        """
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
        """
        Toggles the visibility of the analytics section based on the button click.

        Inputs:
            n_clicks: The number of times the analytics toggle button has been clicked.
            is_open: The current state of the analytics section (whether it's open or closed).

        Outputs:
            is_open: The updated state of the analytics section (open or closed).
        """
        if n_clicks:
            return not is_open
        return is_open
    






# Tap callbacks
def register_cytoscape_callbacks(app):
    
    
    # Tap node data
    @app.callback(
        Output('node-detail', 'children'),
        Output('node-detail', 'style'),
        Output("document-dropdown", "options"),
        [Input("input-company-name", "value"),
        Input('cytoscape-network', 'tapNodeData')]
    )
    def display_node_data(company_name, node_data):
        """
        Displays detailed information about a node when it is clicked in the Cytoscape network.

        Inputs:
            company_name: The name of the company from the search input.
            node_data: Data related to the clicked node, including ID, link, previous names, etc.

        Outputs:
            details: A list of HTML components to display the node's details.
            style: A style dictionary for the node details section.
            options: A list of options for the document dropdown based on the node's company.
        """
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
                html.P(f"Period Ends: {node_data.get('period_end')}"),
                html.Div([
                    html.H5("Previous Names:"),
                    html.Table(
                        # Table header
                        [
                            html.Tr([html.Th("Name"), html.Th("Effective From"), html.Th("Ceased On")])
                        ]
                        +
                        # Table rows for each previous name
                        [
                            html.Tr([
                                html.Td(name.get("name", "N/A")),
                                html.Td(name.get("effective_from", "N/A")),
                                html.Td(name.get("ceased_on", "N/A"))
                            ])
                            for name in node_data.get("previous_names", [])
                        ],
                        style={"width": "100%", "borderCollapse": "collapse"}
                    )
                ])
            ]

            
            # Document search 
            # Needs to be updated somewhere to get filiing history on node tap, populate download that way
            data = utils.fetch_document_records(company_name=node_data.get('label'), cache=cache, company_number=node_data.get('number'))
            if not data or 'items' not in data:
                logging.error(f"Documents list empty for {company_name}")
                return []

            document_list = data['items']

            # logging.info(f"Fetched documents for {node_data.get('label')}: {data}")

            options = utils.get_document_options(document_list)


            return details, {'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px', 'display': 'block'}, options    
        return "", {'display': 'none'}, []

    # tap Edge data
    @app.callback(
        Output('control-info', 'children'),
        Input('cytoscape-network', 'tapEdgeData'),
        Input('cytoscape-network', 'elements')
    )
    def display_edge_info(edge_data, elements):
        """
        Displays information about the edge (relationship) between two nodes when clicked.

        Inputs:
            edge_data: Data related to the clicked edge, including source, target, and nature of control.
            elements: The complete list of elements in the Cytoscape network (nodes and edges).

        Outputs:
            children: A list of HTML components displaying the edge description.
        """
        if edge_data:
            
            source_node_id = edge_data.get('source', '')
            target_node_id = edge_data.get('target', '')
            source_node_name = ''
            target_node_name = ''

            for node in elements:
                if node['data']['id'] == source_node_id:
                    source_node_name = node['data']['label']
                elif node['data']['id'] == target_node_id:
                    target_node_name = node['data']['label']

                      

            nature_of_control = edge_data.get('nature_of_control', "")

            nature_of_control_list = [item.strip() for item in nature_of_control.split(',')] if nature_of_control else []
            

            descriptions = [
                utils.clean_yaml_description(utils.NATURE_OF_CONTROL_DICT.get(control, "Unknown description"))
                for control in nature_of_control_list
            ]

            return [
                html.P(f"{target_node_name} {description} {source_node_name}") for description in descriptions
            ]
        return "Click on an edge to see the nature of control information."


    
    @app.callback(
        Output("download-link", "data"),
        [Input("download-button", "n_clicks")],
        [State("document-dropdown", "value")]
    )
    def download_selected_document(n_clicks, selected_document):
        """
        Handles the download of a selected document when the download button is clicked.

        Inputs:
            n_clicks: The number of times the download button has been clicked.
            selected_document: The ID of the selected document to download.

        Outputs:
            A file object or `no_update` to prevent updates if conditions aren't met.
        """
        if not n_clicks or not selected_document:
            return no_update

        try:
            # Attempt to download the document
            #logging.info(f"Trying to download file {selected_document}")
            file_path = scraper.get_document(selected_document)
            if file_path:
                # Serve the file for download
                logging.info(f"Serving file {file_path} to user.")
                return dcc.send_file(file_path)
        except Exception as e:
            logging.error(f"Failed to process document {selected_document} download: {e}")
            raise RuntimeError(f"Request failed: {e}")
        finally:
            # Cleanup file if it exists
            if 'file_path' in locals() and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logging.info(f"Cleaned up temporary file: {file_path}")
                except Exception as cleanup_error:
                    logging.warning(f"Failed to clean up temporary file {file_path}: {cleanup_error}")




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