import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
import logging
from callbacks import register_callbacks, register_cytoscape_callbacks

app = dash.Dash(__name__)

register_callbacks(app)
register_cytoscape_callbacks(app)

app.title = "Interlocking Directorates Network"

logging.basicConfig(level=logging.INFO)


cytoscape_container = html.Div(
    [
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
    ],
    style={
        'border': '1px solid #ccc',
        'overflow': 'auto',
        'height': '600px',
        'margin-top': '20px',
    }
)

collapsible_analytics = dbc.Collapse(
    [
        html.Div(id='analytics-container', style={'margin': '20px'}),
    ],
    id='collapse-analytics',
    is_open=True
)

analytics_toggle = html.Button(
    "Toggle Analytics",
    id='analytics-toggle',
    n_clicks=0,
    style={'margin': '10px'}
)

download_section = html.Div(
    [
        dcc.Dropdown(
            id="document-dropdown",
            options=[],  # Will be populated dynamically
            placeholder="Select a document to download",
            style={'margin-bottom': '10px'},
            className="dash-dropdown"
        ),
        html.Button("Download", id="download-button", n_clicks=0),
        dcc.Download(id="download-link"),  # Used to handle downloads
    ],
    style={
        "fontSize": "14px",  # Adjust font size
        "lineHeight": "1.5",  # Increase spacing between lines
        "padding": "10px",  # Add padding for a clean look
    }
)

search_history = html.Div(
    [
        html.H3("Search History"),
        dcc.Dropdown(id='search-history-dropdown', options=[], placeholder="Select a past search")
    ], 
    style={'margin-top': '20px'}
)

input_section = html.Div(
    [
        dcc.Input(id='input-company-name', type='text', placeholder='Enter Company Name'),
        html.Button(id='submit-button', n_clicks=0, children='Submit'),
    ],
    className="input-container",
    style={'margin': '20px'}
)

app.layout = html.Div(
    [
        # Main Flex Container
        html.Div(
            [
                # Left Panel
                html.Div(id="left-panel", children=[
                    
                    # Input section
                    input_section,
                    
                    search_history,

                    # Add SME input fields to the left panel
                    html.Div(
                            [
                                html.H3("Document Downloader"),
                                download_section,  # Add this to the layout
                    ], style={'margin': '20px'}),
                ]),

                # Center Panel
                
                html.Div(id="center-panel", children=[
                    dcc.Loading(
                        id='loading',
                        type="default",
                        children=[
                            cytoscape_container
                        ]
                    ),
                    html.Div(id='message', style={'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px', 'display': 'none'}),
                    html.Div(id='dummy-output', style={'display': 'none'}),
                ]),

                # Right Panel
                html.Div(id="right-panel", children=[
                    html.Div(id='node-detail', style={'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px', 'display': 'none'}),

                    # Control Info
                    html.Div(id='control-info', style={'padding': '20px', 'border': '1px solid #ccc', 'margin-top': '20px'}),                    
                    # Analytics
                    html.Div(
                        [
                            analytics_toggle,
                            collapsible_analytics,
                        ],
                        className="analytics-container",
                        style={'margin': '20px'}
                    ),
                ])
            ],
            id="main-flex-container",
        ),
    ]
)



if __name__ == '__main__':
    app.run_server(debug=True)
