from dash import Dash, dcc, html
from dash.dependencies import Input, Output

page_1 = html.Div(
    [
        html.H4("Select value for Profit/Loss Target:"),
        html.Div(
            children=[
                html.P("The default value of Profit/Loss Cap is 20%. ")
        ],
                style={'width': '365px'}
        ),

        html.Div(
            children=[
                html.Div(
                    children=[
                        dcc.Input(id="profitCap", type="number", placeholder="Profit Target"),
                        dcc.Input(id="lossCap", type="number", debounce=True, placeholder="Loss Tolerance",),
                    ]
                ),
            ]
        ),
        html.Br(),

        html.H4("Select Time Limit of Position:"),
        html.Div(
            children=[
                html.P("The default value of position is 2 weeks. "+
                   "Select the amount of time for which the data needs to be retrieved: " +
                   "D (days), W (weeks), M (months).")
            ],
        ),

         html.Div(
             children=[
                 html.Div(
                     children=[
                         dcc.Input(id='duration-str-number', value='2', debounce=True)
                     ],
                     style={
                         'display': 'inline-block',
                         'margin-right': '20px',
                     }
                 ),
                 html.Div(
                     children=[
                         dcc.Dropdown(
                             ["D", "W", "M"], "W", id='duration-str-unit'),
                     ],
                     style={
                         'display': 'inline-block',
                         'padding-right': '100px'
                     }
                 ),
             ]
         ),
        html.Br(),

        # Submit button
        html.Button('Confirm', id='confirm-button', n_clicks=0),
    ]
)



