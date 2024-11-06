# simple map ui, no server


def create_map_html(true_location, noisy_location, nearby_users=None):
    nearby_users_points = []
    if nearby_users:
        for user in nearby_users:
            s = f"""
                var userMarker = L.marker([{user['location']['latitude']}, {user['location']['longitude']}], {{ icon: nearbyMarker }}).addTo(map)
                    .bindPopup(`<strong>Nearby User</strong><br>User ID: {user['user_id']}<br>Distance: {user['distance']} km`);
                userMarker.on('mouseover', function(e) {{
                    info.update({{name: '{user['user_id']}', distance: '{user['distance']} km', user_id: '{user['user_id']}'}}); 
                }});
                userMarker.on('mouseout', function(e) {{
                    info.update();
                }});
                """
            nearby_users_points.append(s)
    nearby_users_str = "\n".join(nearby_users_points)


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
                
                var nearbyMarker = L.divIcon({
                    className: 'custom-marker',
                    html: '<div style="background: green; border-radius: 50%; width: 10px; height: 10px; border: 2px solid white;"></div>',
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
                background: rgba(255, 255, 255, 0.8);
                padding: 10px;
                border-radius: 10px;
            }}
            .info {{
                padding: 6px 8px;
                font: 14px/16px Arial, Helvetica, sans-serif;
                background: white;
                background: rgba(255,255,255,0.8);
                box-shadow: 0 0 15px rgba(0,0,0,0.2);
                border-radius: 5px;
                min-width: 180px;
            }}
            .info h4 {{
                margin: 0 0 5px;
                color: #777;
            }}
        </style>
    </head>
    <body>

    <div id="map"></div>


    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
            integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo="
            crossorigin=""></script>
    <script>
        // map centered on the true location
        const map = L.map('map').setView([{true_location[0]}, {true_location[1]}], 13);

        // base tile layer
        L.tileLayer('{tile_str}', {{
            maxZoom: 18,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }}).addTo(map);

        // circle around noisy location
        L.circle([{noisy_location[0]}, {noisy_location[1]}], {{
            color: 'blue',
            fillColor: 'blue',
            fillOpacity: 0.3,
            radius: 5000
        }}).addTo(map);
        
        // circle around true location (3 km radius)
        L.circle([{true_location[0]}, {true_location[1]}], {{
            color: 'black',
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
        
        // Nearby Users
        {nearby_users_str}
        
        L.control.scale({{position:'bottomright', metric: true, imperial: false}}).addTo(map);
        
        // legend
        var legend = L.control({{position: 'topright'}});
        legend.onAdd = function (map) {{
            var div = L.DomUtil.create('div', 'info legend');
            div.innerHTML = `
                <strong>Legend:</strong><br>
                <span style="color:black;">● True Location</span><br>
                <span style="color:blue;">● Noisy Location</span><br>
                <span style="color:green;">● Nearby User</span
            `;
            return div;
        }};
        legend.addTo(map);
        
        
        // Custom Info Control    
        var info = L.control();
        info.onAdd = function (map) {{
            this._div = L.DomUtil.create('div', 'info'); // create a div with a class "info"
            this.update();
            return this._div;
        }};

        // method that we will use to update the control based on feature properties passed
        info.update = function (props) {{
            this._div.innerHTML = '<h4>Nearby User Info</h4>' +  (props ?
                '<b>' + props.name + '</b><br/>' + props.distance + ' (from noisy location)'
                : 'Hover over a green point');
        }};
        
        function highlightFeature(e) {{
            info.update(layer.feature.properties);
        }}
        
        function resetHighlight(e) {{
            info.update();
        }}

        info.addTo(map);

    </script>
    </body>
    </html>
    """

    # write to file
    filename = "map.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)

    return filename
