import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from kafka import KafkaConsumer
import json
import threading
import time
from collections import defaultdict
import re
import os
from ollama_call import query_ollama

# Add debug flag
DEBUG = False

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
            if DEBUG and message_count % 10 == 0:
                print(f"Received message #{message_count}")
            
            message_str = message.value.decode('utf-8')
            json_str = message_str.replace('}{', '}\n{')
            
            for json_obj in json_str.split('\n'):
                data = json.loads(json_obj)
                
                icao24 = data.get('icao24')
                if icao24:
                    lat = data.get('latitude')
                    lon = data.get('longitude')
                    
                    if lat is not None and lon is not None:
                        aircraft_positions[icao24] = {
                            'lat': float(lat),
                            'lon': float(lon),
                            'callsign': data.get('callsign', '').strip(),
                            'altitude': data.get('altitude'),
                            'country': data.get('orig_country'),
                            'last_update': data.get('time'),
                            'icao24': icao24,
                            'velocity': data.get('velocity'),
                            'vertical_rate': data.get('vertical_rate'),
                            'true_track': data.get('true_track')
                        }
                        
                        if DEBUG and len(aircraft_positions) % 5 == 0:
                            print(f"Now tracking {len(aircraft_positions)} aircraft")
            
            # Remove stale aircraft data
            current_time = time.time()
            stale_aircraft = [aircraft_id for aircraft_id, aircraft_data in aircraft_positions.items()
                              if current_time - aircraft_data.get('last_update', 0) > 300]
            
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

# Create Dash app

assets_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
app = dash.Dash(__name__, 
                assets_folder=assets_folder,
                meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}])

app.layout = html.Div([
    html.Div([
        html.H1("Open Sky Object Tracker", className='dashboard-title'),
        html.Div([
            html.Div([
                html.H3("Aircraft Count: ", style={'display': 'inline-block'}),
                html.Span(id='aircraft-count', children="0", className='aircraft-count')
            ]),
            html.Div(id='debug-info', className='debug-info'),
        ], className='info-container'),
        dcc.Graph(id='live-map', className='live-map'),
    ], className='dashboard-section'),
    
    html.Div([
        html.H2("Ask about Flight Data"),
        dcc.Input(
            id='llm-query-input', 
            type='text', 
            placeholder='Ask about the flight data',
            className='query-input'
        ),
        html.Button('Ask LLM', id='llm-query-button', className='query-button'),
        html.Div(id='llm-response', className='query-response'),
    ], className='dashboard-section query-section'),
    
    dcc.Interval(
        id='interval-component',
        interval=2*1000,
        n_intervals=0
    )
], className='main-container')

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
                size=10,  # Increased size for better visibility
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
    
    # Configure the map
    fig.update_layout(
        geo = dict(scope='europe'),
        margin={"r":0,"t":0,"l":0,"b":0},
        uirevision='constant'  # This prevents map from resetting on updates
    )
    
    return fig, str(len(aircraft_positions)), debug_text

@app.callback(
    Output('llm-response', 'children'),
    Input('llm-query-button', 'n_clicks'),
    State('llm-query-input', 'value'),
    prevent_initial_call=True
)
def update_llm_response(n_clicks, query=None):
    if query is None or query.strip() == "":
        query = "Give me a summary of the current flight data"
    
    # Prepare context from aircraft data
    context = "You shall not return SQL queries but return information yourself,\n Current data:\n"
    for icao24, data in list(aircraft_positions.items())[:70]:  # Limit to 70 aircraft for brevity
        context += f"Aircraft {icao24}: Callsign: {data['callsign']}, "
        context += f"Latitude: {data['lat']}, Longitude: {data['lon']}, "
        context += f"Altitude: {data['altitude']}, Country: {data['country']}\n"
    
    # Combine context and query
    full_prompt = f"{context}\n\nUser query: {query}\n\nResponse:"
    
    try:
        response = query_ollama(full_prompt)
        return [response]  # Return as a list with a single element
    except Exception as e:
        return [f"Error processing query: {str(e)}"]  # Return as a list with a single element



if __name__ == '__main__':
    print("Starting Flight Tracker application...")
    print(f"Currently tracking {len(aircraft_positions)} aircraft (including samples)")
    print("Access the dashboard at http://localhost:8050")
    app.run_server(debug=True, host='0.0.0.0', port=8050)