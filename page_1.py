import dash
import pandas as pd
import final_project as fp
from dash import dcc, html, callback, dash_table
from dash.dependencies import Input, Output, State

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
    # Divs that only serve as a state holder
    html.Div(id='run-button-disabled', children=0, style=dict(display='none')),
    html.Div(id='run-button-enabled', children=0, style=dict(display='none')),
    html.Br(),
    html.Hr(),
    dcc.Loading(
        id="loading-1",
        type="default",
        children=html.Div(id='output-container',
                          style={'text-align': 'center'},
                          children=[
                              html.H4("Output Messages", style={'text-align': 'center'}),
                              html.Br(),
                              html.Div(id='total-orders-output', children='No messages',
                                       style={'text-align': 'center',
                                              'display': 'inline-block',
                                              'vertical-align': 'top',
                                              'width': '25%'}),
                              html.Div(id='amzn-output', children='No messages',
                                       style={'text-align': 'center',
                                              'display': 'inline-block',
                                              'vertical-align': 'top',
                                              'width': '25%'}),
                              html.Div(id='wmt-output', children='No messages',
                                       style={'text-align': 'center',
                                              'display': 'inline-block',
                                              'vertical-align': 'top',
                                              'width': '25%'}),
                              html.Div(id='total-gain-loss-output', children='No messages',
                                       style={'text-align': 'center',
                                              'display': 'inline-block',
                                              'vertical-align': 'top',
                                              'width': '25%'}),
                              html.Br(),
                              html.Br(),
                              html.H4("Blotter", style={'text-align': 'center'}),
                              html.Div(
                                  children=[
                                      dash_table.DataTable(
                                          columns=[{"name": i, "id": i} for i in blotter_data.columns],
                                          page_size=50,
                                          export_format="csv",
                                          id='blotter-data-tbl'
                                      )],
                                  style={'width': '50%', 'margin': '0 auto'}
                              )
                          ]),
    ),
])


# This callback only cares about the input event, not its value
# This is called if both events happen together or if only one happens
@callback(
    Output(component_id='run-backtest-button', component_property='disabled'),
    Input('run-button-disabled', 'children'),
    Input('run-button-enabled', 'children'),
)
def should_disable_submit_button(should_disable, should_enable):
    if len(dash.callback_context.triggered) == 1:
        context = dash.callback_context.triggered[0]['prop_id'].split('.')[0]
        return context == 'run-button-disabled'


# Breaking the process into 2 separate triggers.
# Rationale: If 'should_disable_button' waits for either 'run-backtest-button' or 'candlestick-graph' directly,
# Dash only delivers those events together to 'should_disable_button'
@callback(
    Output(component_id='run-button-disabled', component_property='children'),
    Input('run-backtest-button', 'n_clicks'),
)
def trigger_disable_submit_button(n_click):
    return 1


@callback(
    Output(component_id='run-button-enabled', component_property='children'),
    Input('total-orders-output', 'children'),
)
def trigger_enable_submit_button(n_click):
    return 1


@callback(
    [Output(component_id='blotter-data-tbl', component_property='data'),
     Output(component_id='total-orders-output', component_property='children'),
     Output(component_id='amzn-output', component_property='children'),
     Output(component_id='wmt-output', component_property='children'),
     Output(component_id='total-gain-loss-output', component_property='children')],
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
    messages = fp.get_stats(history, blotter)
    order_messages = [html.P(x) for x in messages[0]]
    amzn_messages = [html.P(x) for x in messages[1]]
    wmt_messages = [html.P(x) for x in messages[2]]
    gain_loss_messages = [html.P(x) for x in messages[3]]
    return blotter.to_dict(orient='records'), order_messages, amzn_messages, wmt_messages, gain_loss_messages
