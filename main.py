import dash
from dash import html, dcc
from dash.dependencies import Input, Output
import dash_cytoscape as cyto
import logging
from callbacks import register_callbacks, register_cytoscape_callbacks

app = dash.Dash(__name__)

register_callbacks(app)
register_cytoscape_callbacks(app)

app.title = "Interlocking Directorates Network"

logging.basicConfig(level=logging.INFO)


app.layout = html.Div([
    html.H1("Interlocking Directorates Network"),
    html.Div([
        dcc.Input(id='input-company-name', type='text', placeholder='Enter Company Name'),
        html.Button(id='submit-button', n_clicks=0, children='Submit'),
        #html.Button(id='reset-button', n_clicks=0, children='Reset View'), 
    ],
    className="input-container"),
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


if __name__ == '__main__':
    app.run_server(debug=True)
