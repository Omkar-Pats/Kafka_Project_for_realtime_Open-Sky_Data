import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from kafka import KafkaConsumer
import json
import threading
import time
from collections import defaultdict
import re

# Add debug flag
DEBUG = True

# Initialize Kafka consumer with proper topic name
consumer = KafkaConsumer(
    'Experiment',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='latest',
    # Remove the value_deserializer since we need to handle the raw message
    session_timeout_ms=30000,
    request_timeout_ms=40000
)

# Store the latest aircraft positions
aircraft_positions = {}
message_count = 0  # Add counter for debugging

# Function to consume Kafka messages in background
def consume_messages():
    global message_count
    if DEBUG:
        print("Starting Kafka consumer thread...")
    
    for message in consumer:
        try:
            message_count += 1
            if DEBUG and message_count % 10 == 0:  # Log every 10th message
                print(f"Received message #{message_count}")
            
            # Get the raw message value and decode it
            message_str = message.value.decode('utf-8')
            if DEBUG and message_count <= 3:
                print(f"Raw message: {message_str}")
            
            # Split the concatenated JSON objects
            # Replace }{ with }\n{ to separate JSON objects
            json_str = message_str.replace('}{', '}\n{')
            
            # Process each JSON object
            for json_obj in json_str.split('\n'):
                try:
                    # Parse the JSON string into a Python dictionary
                    data = json.loads(json_obj)
                    
                    if DEBUG and message_count <= 3:
                        print(f"Parsed JSON: {data}")
                    
                    # Extract data from your specific message format
                    icao24 = data.get('icao24')
                    if icao24:
                        # Handle potential None values for coordinates
                        lat = data.get('latitude')
                        lon = data.get('longitude')
                        
                        # Only add aircraft with valid coordinates
                        if lat is not None and lon is not None:
                            aircraft_positions[icao24] = {
                                'lat': float(lat),
                                'lon': float(lon),
                                'callsign': data.get('callsign', '').strip(),
                                'altitude': data.get('altitude'),
                                'country': data.get('orig_country'),
                                'last_update': data.get('time'),
                                'icao24': icao24
                            }
                            
                            if DEBUG and len(aircraft_positions) % 5 == 0:
                                print(f"Now tracking {len(aircraft_positions)} aircraft")
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON object: {e}")
                    print(f"Problematic JSON: {json_obj}")
                
            # Optional: Remove aircraft that haven't been updated in a while
            current_time = time.time()
            stale_aircraft = []
            for aircraft_id, aircraft_data in aircraft_positions.items():
                if current_time - aircraft_data.get('last_update', 0) > 300:  # 5 minutes
                    stale_aircraft.append(aircraft_id)
            
            for aircraft_id in stale_aircraft:
                del aircraft_positions[aircraft_id]
                
        except Exception as e:
            print(f"Error processing message: {e}")
            if DEBUG:
                import traceback
                traceback.print_exc()

# Start Kafka consumer in a separate thread
kafka_thread = threading.Thread(target=consume_messages, daemon=True)
kafka_thread.start()

# Add sample data immediately - don't wait
print("Adding sample data for testing...")
aircraft_positions["sample1"] = {
    'lat': 47.405,
    'lon': 7.4635,
    'callsign': "SWR4QF",
    'altitude': 6873.24,
    'country': "Switzerland",
    'last_update': time.time(),
    'icao24': "sample1"
}
aircraft_positions["sample2"] = {
    'lat': 47.505,
    'lon': 7.5635,
    'callsign': "TEST123",
    'altitude': 5000.0,
    'country': "Test Country",
    'last_update': time.time(),
    'icao24': "sample2"
}
aircraft_positions["sample3"] = {
    'lat': 47.605,
    'lon': 7.9635,
    'callsign': "DEMO456",
    'altitude': 8000.0,
    'country': "Demo Country",
    'last_update': time.time(),
    'icao24': "sample3"
}
print(f"Added {len(aircraft_positions)} sample aircraft")

# Create Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Open Sky API Object Tracker Tracker"),
    html.Div([
        html.Div([
            html.H3("Aircraft Count: "),
            html.Span(id='aircraft-count', children="0")
        ], style={'marginBottom': '10px'}),
        html.Div(id='debug-info', children="Waiting for data...", style={'marginBottom': '10px'}),
        dcc.Graph(id='live-map', style={'height': '80vh'}),
    ]),
    dcc.Interval(
        id='interval-component',
        interval=2*1000,  # Update every 2 seconds
        n_intervals=0
    )
])

@app.callback(
    [Output('live-map', 'figure'),
     Output('aircraft-count', 'children'),
     Output('debug-info', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_map(n):
    # Extract position data for plotting
    positions = list(aircraft_positions.values())
    
    # Debug info with more details
    debug_text = f"Messages received: {message_count}, Aircraft tracked: {len(positions)}"
    if positions:
        debug_text += f" | Sample position: Lat={positions[0].get('lat')}, Lon={positions[0].get('lon')}"
    
    # Create hover text with aircraft details
    hover_texts = []
    for pos in positions:
        text = f"Callsign: {pos.get('callsign', 'N/A')}<br>"
        text += f"ICAO24: {pos.get('icao24', 'N/A')}<br>"
        text += f"Altitude: {pos.get('altitude', 'N/A')} ft<br>"
        text += f"Country: {pos.get('country', 'N/A')}"
        hover_texts.append(text)
    
    # Create the map with aircraft markers
    fig = go.Figure()
    
    # Extract lat/lon values and ensure they are valid numbers
    lats = []
    lons = []
    texts = []
    valid_hover_texts = []
    
    for i, pos in enumerate(positions):
        try:
            lat = float(pos.get('lat', 0))
            lon = float(pos.get('lon', 0))
            
            # Only add valid coordinates
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                lats.append(lat)
                lons.append(lon)
                texts.append(pos.get('callsign', ''))
                valid_hover_texts.append(hover_texts[i])
            else:
                print(f"Invalid coordinates: lat={lat}, lon={lon} for {pos.get('icao24')}")
        except (ValueError, TypeError) as e:
            print(f"Error with coordinates for {pos.get('icao24')}: {e}")
    
    if lats and lons:  # Only add trace if we have valid coordinates
        fig.add_trace(go.Scattergeo(
            lat=lats,
            lon=lons,
            mode='markers',
            marker=dict(
                size=15,  # Increased size for better visibility
                color='red',
                opacity=0.8,
                symbol='arrow-open',
            ),
            text=texts,
            textposition="top center",
            hoverinfo="text",
            hovertext=valid_hover_texts,
            name="Aircraft"
        ))
        
        debug_text += f" | Plotted {len(lats)} valid aircraft"
    else:
        debug_text += " | No valid coordinates to plot"
    
    # Set initial map center - use average position or default
    center_lat = 47.4  # Default to Switzerland area based on your sample
    center_lon = 8.5
    
    if lats and lons:
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
    
    # Configure the map
    fig.update_layout(
        geo = dict(scope='europe'),
        margin={"r":0,"t":0,"l":0,"b":0},
        uirevision='constant'  # This prevents map from resetting on updates
    )
    
    return fig, str(len(aircraft_positions)), debug_text

if __name__ == '__main__':
    print("Starting Flight Tracker application...")
    print(f"Currently tracking {len(aircraft_positions)} aircraft (including samples)")
    print("Access the dashboard at http://localhost:8050")
    app.run_server(debug=True, host='0.0.0.0', port=8050)