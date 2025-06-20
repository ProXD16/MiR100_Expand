import rospy
from geometry_msgs.msg import Twist
from dash import Dash, html, dcc
from dash.dependencies import Input, Output, State
import dash_daq as daq
import math

# ROS node initialization
rospy.init_node('mir_joystick_interface', anonymous=True)
pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

# Dash app setup
app = Dash(__name__, suppress_callback_exceptions=True)
app.title = "MiR Joystick Controller"

# Layout with enhanced styling and additional controls
app.layout = html.Div([
    html.H2("🚀 MiR Robot Joystick Control", style={
        'textAlign': 'center',
        'color': '#2c3e50',
        'marginBottom': '30px'
    }),

    html.Div([
        daq.Joystick(
            id='joystick',
            label="Control Joystick",
            size=200,
            style={'margin': 'auto'}
        ),
        
        # Speed scale slider wrapped in a Div for styling
        html.Label("Speed Scale:", style={'marginTop': '20px'}),
        html.Div([
            dcc.Slider(
                id='speed-scale',
                min=0.1,
                max=1.0,
                step=0.1,
                value=0.5,
                marks={i/10: str(i/10) for i in range(1, 11)},
                updatemode='drag'
            )
        ], style={'width': '300px', 'margin': '20px auto'}),

        # Emergency stop button
        daq.BooleanSwitch(
            id='emergency-stop',
            on=False,
            label="Emergency Stop",
            labelPosition="top",
            color="#ff0000",
            style={'margin': '20px auto'}
        ),
    ], style={'textAlign': 'center'}),

    dcc.Interval(id='interval-pub', interval=50, n_intervals=0),  # 50ms for smoother control

    html.Div(id='joystick-output', style={
        'marginTop': '30px',
        'fontSize': '20px',
        'color': '#34495e',
        'textAlign': 'center'
    }),

    dcc.Store(id='joystick-data', data={'angle': 0, 'force': 0})
], style={
    'maxWidth': '600px',
    'margin': 'auto',
    'padding': '20px',
    'backgroundColor': '#f9f9f9',
    'borderRadius': '10px',
    'boxShadow': '0 4px 8px rgba(0,0,0,0.1)'
})

# Callback to store joystick data
@app.callback(
    Output('joystick-data', 'data'),
    Input('joystick', 'angle'),
    Input('joystick', 'force')
)
def update_joystick_data(angle, force):
    return {'angle': angle or 0, 'force': force or 0}

# Callback to send Twist commands and update display
@app.callback(
    Output('joystick-output', 'children'),
    Input('interval-pub', 'n_intervals'),
    State('joystick-data', 'data'),
    State('speed-scale', 'value'),
    State('emergency-stop', 'on')
)
def send_twist(n, data, speed_scale, emergency_stop):
    if emergency_stop:
        twist = Twist()  # Send stop command
        pub.publish(twist)
        return "🛑 Emergency Stop Activated!"

    angle = data['angle']
    force = data['force']

    if force == 0:
        twist = Twist()  # Send stop command
        pub.publish(twist)
        return "⏹ Robot Stopped"

    # Normalize angle to [0, 360) degrees
    angle = angle % 360

    # Calculate linear and angular velocities based on joystick direction
    linear = 0.0
    angular = 0.0

    # Linear velocity (up/down): map vertical component
    # Up (angle ~0°) = forward, Down (angle ~180°) = backward
    linear = math.sin(math.radians(angle)) * force * speed_scale
    # Scale linear velocity to max 1.0 m/s
    linear = max(min(linear, 1.0), -1.0)

    # Angular velocity (left/right): map horizontal component
    # Left (angle ~90°) = counter-clockwise, Right (angle ~270°) = clockwise
    angular = math.cos(math.radians(angle)) * force * speed_scale * 2.0
    # Scale angular velocity to max 2.0 rad/s
    angular = max(min(angular, 1.5), -1.5)
    

    # Publish Twist message
    twist = Twist()
    twist.linear.x = linear
    twist.angular.z = angular
    pub.publish(twist)

    return f"🚀 Moving: Linear = {linear:.2f} m/s, Angular = {angular:.2f} rad/s"

# Run Dash app
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8050)