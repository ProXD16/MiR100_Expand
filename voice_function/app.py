from dash import Dash
from layout import setup_layout
from callback import setup_callback


app = Dash(__name__, title="Voice GUI")
app.layout = setup_layout()

setup_callback(app)

if __name__ == "__main__":
    app.run(debug=True, port=1607)
