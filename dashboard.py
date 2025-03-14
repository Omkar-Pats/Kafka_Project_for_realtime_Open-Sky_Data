import json
import pandas as pd
import folium
import uuid
import os
from streamlit.components.v1 import html

def create_map_html():
    """Create the initial map HTML with JavaScript for updates"""
    # Create a map centered on Switzerland
    m = folium.Map(location=[46.8182, 8.2275], zoom_start=7)
    
    # Generate a unique ID for the map
    map_id = f"map_{uuid.uuid4().hex}"
    
    # Get the map HTML
    map_html = m._repr_html_()
    
    # Add Font Awesome for plane icons
    map_html = map_html.replace('</head>', 
                               '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css"></head>')
    
    # Read JavaScript from file
    js_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'flight_tracker.js')
    try:
        with open(js_file_path, 'r') as js_file:
            js_code = js_file.read()
    except FileNotFoundError:
        # If file not found, create the directory and provide a message
        os.makedirs(os.path.dirname(js_file_path), exist_ok=True)
        js_code = """
        console.error("JavaScript file not found. Please create the file at: " + "{js_file_path}");
        function updateFlightMarkers() {
            console.error("Flight tracker JavaScript not loaded");
        }
        """
    
    # Add the JavaScript to the HTML
    map_html = map_html.replace('</body>', f'<script>{js_code}</script></body>')
    
    return map_html, map_id

def update_flight_data_js(df):
    """Convert DataFrame to JSON for JavaScript updates"""
    # Rename columns to match JavaScript expectations
    df_copy = df.copy()
    
    # Convert column names to lowercase
    df_copy.columns = [col.lower() for col in df_copy.columns]
    
    # Ensure we have the expected columns
    required_columns = ['icao24', 'latitude', 'longitude', 'altitude', 'callsign', 'orig_country', 'time']
    for col in required_columns:
        if col not in df_copy.columns:
            df_copy[col] = None
    
    # Convert DataFrame to list of dictionaries
    flight_data = df_copy.to_dict('records')
    
    # Convert datetime objects to strings and handle NaN values
    for flight in flight_data:
        for key, value in flight.items():
            if pd.isna(value):
                flight[key] = None
            elif isinstance(value, pd.Timestamp):
                flight[key] = value.strftime('%Y-%m-%d %H:%M:%S')
    
    # Convert to JSON
    return json.dumps(flight_data)

            