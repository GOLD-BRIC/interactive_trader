import dash
import pandas as pd
import final_project as fp
from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output, State
import dash_daq as daq

blotter_data = pd.DataFrame(
    columns=['Date', 'Symbol', 'Trip', 'Action', 'Price', 'Size', 'Status'])

page_1 = html.Div([
    html.H4("Select period of days for correlation coefficient:"),
    html.Div(
        children=[
            html.P("The minimum value is 3 business days. ")
        ],
        style={'width': '365px'}
    ),
    html.Div(
        children=[
            dcc.Input(id="corr-coef-period", type="number", min=3, value=3, placeholder="Business Days"),
        ]
    ),
    html.Br(),

    html.H4("Select dollar amount for each trade:"),
    html.Div(
        children=[
            html.P("The minimum value is $10,000. ")
        ],
        style={'width': '365px'}
    ),
    html.Div(children=[
        dcc.Input(id="trade-lot", type="number", min=10000, value=25000, placeholder="Dollar amount"),
    ]
    ),
    html.Br(),

    html.H4("Select the gain cap in percentage:"),
    html.Div(
        children=[
            dcc.Input(id="gain-cap", type="number", min=0, value=10, placeholder="10%", style={'width': '4%'}),
            html.Span(' in percentage (%)')
        ]
    ),
    html.Br(),

    html.H4("Select if risk-free should be taken into consideration:"),
    html.Div(children=[
        dcc.RadioItems(
            id='risk-free-flag',
            options=[
                {'label': 'True', 'value': 'True'},
                {'label': 'False', 'value': 'False'}
            ],
            value='False'
        ),
    ]
    ),
    html.Br(),

    html.H4("Select holding period cap:"),
    html.Div(
        children=[
            html.P("The minimum value is 1 business day. ")
        ],
        style={'width': '365px'}
    ),
    html.Div(children=[
        dcc.Input(id="holding-period-cap", type="number", min=1, value=5, placeholder="Business days"),
    ]),
    html.Br(),

    html.Button('Run Backtest', id='run-backtest-button', n_clicks=0, disabled=False),
    html.Div(
        children=[
            dash_table.DataTable(
                columns=[{"name": i, "id": i} for i in blotter_data.columns],
                id='blotter-data-tbl'
            )],
        style={'width': '50%', 'margin': '0 auto'}
    )

])


@callback(
    Output(component_id='blotter-data-tbl', component_property='data'),
    Input('run-backtest-button', 'n_clicks'),
    [State('corr-coef-period', 'value'),
     State('trade-lot', 'value'),
     State('gain-cap', 'value'),
     State('risk-free-flag', 'value'),
     State('holding-period-cap', 'value')],

    prevent_initial_call=True
)
def run_backtest(n_clicks, period, trade_lot, gain_cap_perc, risk_free_flag, holding_period_cap):
    gain_cap = round(gain_cap_perc / 100, 2)
    is_risk_free = risk_free_flag == 'True'
    history = fp.load_data(period)
    print(f'Inputs: period={period}, trade_lot={trade_lot}, '
          f'gain_cap={gain_cap}, is_risk_free={is_risk_free},'
          f'holding_period={holding_period_cap}')
    blotter = fp.run_backtest(history, period, trade_lot, gain_cap, is_risk_free, holding_period_cap)
    here = fp.get_stats(history, blotter)
    print("#######################################")
    print(here)
    return blotter.to_dict(orient='records')
