from dash import Dash, dcc, html
from dash.dependencies import Input, Output

app = Dash(__name__)
app.layout = html.Div(
    [
        dcc.Input(id="lossCap", type="number", placeholder="Loss Tolerance"),
        dcc.Input(
            id="profitCap", type="number",
            debounce=True, placeholder="Profit Target",
        ),

        html.Hr(),
        html.Div(id="number-out"),
    ]
)


@app.callback(
    Output("number-out", "children"),
    Input("lossCap", "value"),
    Input("profitCap", "value"),
)
def number_render(fval, tval):
    return "lossCap: {}, profitCap: {}".format(fval, tval)


if __name__ == "__main__":
    app.run_server(debug=True)
