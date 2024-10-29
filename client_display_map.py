# simple map ui, no server



def create_map_html(true_location, noisy_location):
    tile_str = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"

    custom = """// Custom Marker Style
                var trueMarker = L.divIcon({
                    className: 'custom-marker',
                    html: '<div style="background: black; border-radius: 50%; width: 14px; height: 14px; border: 2px solid white;"></div>',
                    iconSize: [20, 20],
                    iconAnchor: [10, 20]
                });
                
                var noisyMarker = L.divIcon({
                    className: 'custom-marker',
                    html: '<div style="background: blue; border-radius: 50%; width: 14px; height: 14px; border: 2px solid white;"></div>',
                    iconSize: [20, 20],
                    iconAnchor: [10, 20]
                });
            """

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Location Privacy Visualization</title>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
              integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
              crossorigin=""/>
        <style>
            body {{
                padding-inline: 3rem;
            }}
            #map {{
                height: 600px;
                width: 100%;
            }}
            .legend {{
                background: white;
                padding: 10px;
            }}
        </style>
    </head>
    <body>

    <div id="map"></div>
    <div class="legend">
        <strong>Legend:</strong><br>
        <span style="color:blue;">● True Location</span><br>
        <span style="color:black;">● Noisy Location</span>
    </div>

    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
            crossorigin=""></script>
    <script>
        // Initialize the map centered on the true location
        const map = L.map('map').setView([{true_location[0]}, {true_location[1]}], 13);

        // Add the base tile layer from OpenStreetMap
        L.tileLayer('{tile_str}', {{
            maxZoom: 18,
            attribution: '© OpenStreetMap contributors'
        }}).addTo(map);

        // Add a circle around the true location (3 km radius)
        L.circle([{true_location[0]}, {true_location[1]}], {{
            color: 'blue',
            fillColor: '#30f',
            fillOpacity: 0.5,
            radius: 3000
        }}).addTo(map);
        
        {custom}
        
        // True Location Marker
        L.marker([{true_location[0]}, {true_location[1]}], {{ icon: trueMarker }}).addTo(map)
            .bindPopup(`<strong>True Location</strong><br>Lat: {true_location[0]}<br>Lng: {true_location[1]}`);
        
        // Noisy Location Marker
        L.marker([{noisy_location[0]}, {noisy_location[1]}], {{ icon: noisyMarker }}).addTo(map)
            .bindPopup(`<strong>Noisy Location</strong><br>Lat: {noisy_location[0]}<br>Lng: {noisy_location[1]}`);
        
        
    </script>
    </body>
    </html>
    """

    # write to file
    f = "map.html"
    with open(f, "w", encoding="utf-8") as f:
        f.write(html_content)

    return f


"""

    // True Location Marker
    L.marker([{true_location[0]}, {true_location[1]}], {{
        icon: L.icon({{
            iconUrl: 'https://leafletjs.com/examples/custom-icons/leaf-green.png',
            iconSize: [38, 95],
            iconAnchor: [19, 95]
        }})
    }}).addTo(map)
        .bindPopup(`<strong>True Location</strong><br>Lat: {true_location[0]}<br>Lng: {true_location[1]}`);
    
    // Noisy Location Marker
    L.marker([{noisy_location[0]}, {noisy_location[1]}], {{
        icon: L.icon({{
            iconUrl: 'https://leafletjs.com/examples/custom-icons/leaf-red.png',
            iconSize: [38, 95],
            iconAnchor: [19, 95]
        }})
    }}).addTo(map)
        .bindPopup(`<strong>Noisy Location</strong><br>Lat: {noisy_location[0]}<br>Lng: {noisy_location[1]}`);


"""