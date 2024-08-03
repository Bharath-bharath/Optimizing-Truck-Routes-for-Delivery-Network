"""-----------------------------------------------------------------------------------"""
"""                                       Working attempt-1                           """
"""-----------------------------------------------------------------------------------"""
from flask import Flask, render_template, request, redirect, url_for, jsonify
import cx_Oracle
from openrouteservice import Client
import polyline
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import os
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime


app = Flask(__name__)

# Oracle database connection string
orcl_connect_str = 'system/orcl7bharath@localhost:1521/XE'
connection = cx_Oracle.connect(orcl_connect_str)
cursor = connection.cursor()

# Route for index page
@app.route('/')
def index():
    return render_template('index.html')

# Route to delivery creation page
@app.route('/owner_page')
def owner_page():
    return render_template('owner_page.html')

# Function for storing the input to database
@app.route('/submit_locations', methods=['POST'])
def submit_locations():
    location_counter = 0
    while True:
        location_counter += 1
        store_name = request.form.get(f'store_name_{location_counter}')
        mobile_number = request.form.get(f'mobile_number_{location_counter}')
        location_name = request.form.get(f'location_name_{location_counter}')
        latitude = request.form.get(f'latitude_{location_counter}')
        longitude = request.form.get(f'longitude_{location_counter}')
        priority = request.form.get(f'priority_{location_counter}')

        if not store_name or not mobile_number or not location_name or not latitude or not longitude:
            break

        try:
            cursor.execute("""
                INSERT INTO location_info (store_name, mobile_number, location, latitude, longitude, priority)
                VALUES (:1, :2, :3, :4, :5, :6)
            """, (
                store_name,
                mobile_number,
                location_name,
                float(latitude),
                float(longitude),
                int(priority) if priority else None
            ))
        except cx_Oracle.DatabaseError as e:
            connection.rollback()
            print(f"Database error: {e}")
            break

    connection.commit()
    return redirect(url_for('owner_page'))

# Function to delete the records from the database
@app.route('/delete_location/<int:location_counter>', methods=['GET'])
def delete_location(location_counter):
    try:
        store_name = request.args.get('store_name')
        location = request.args.get('location')
        # Use store_name and location to delete from the database
        cursor.execute("DELETE FROM location_info WHERE store_name = :1 AND location = :2", (store_name, location))
        connection.commit()
    except cx_Oracle.DatabaseError as e:
        connection.rollback()
        print(f"Database error: {e}")

    return redirect(url_for('owner_page'))



# Function to calculate the distance between two coordinates
def calculate_distance(loc1, loc2):
    R = 6371000.0  # Radius of the Earth in meters

    lat1 = radians(loc1[1])
    lon1 = radians(loc1[0])
    lat2 = radians(loc2[1])
    lon2 = radians(loc2[0])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    return distance

# Function to calculate the route
def calculate_route(start, end, stops, api_key):
    client = Client(key=api_key)

    coordinates = [start] + [stop['location'] for stop in stops] + [end]

    # Calculate the total distance of the route
    total_distance = 0
    for i in range(len(coordinates) - 1):
        total_distance += calculate_distance(coordinates[i], coordinates[i + 1])
    
    print(f"Total Distance: {total_distance} meters")

    if total_distance > 6000000.0:
        print("Error: Total route distance exceeds the limit.")
        return None

    try:
        directions = client.directions(coordinates=coordinates)
    except Exception as e:
        print(f"Error in directions API call: {e}")
        return None

    if 'routes' in directions and len(directions['routes']) > 0:
        geometry = directions['routes'][0]['geometry']
        route_coordinates = polyline.decode(geometry)
        return route_coordinates
    else:
        print("No routes found in directions:", directions)
        return None


import os

# Function to plot the route
def plot_route(route_coordinates, locations):
    if route_coordinates:
        lats, lons = zip(*route_coordinates)

        plt.figure(figsize=(10, 6))

        # Load map image
        map_img = np.array(Image.open(r'C:\Users\BHARATH\adsa_2024\PROJECT\new_attempt\project\static\gmap.png'))

        # Determine the extent of the map image
        min_lon, max_lon = min(lons), max(lons)
        min_lat, max_lat = min(lats), max(lats)
        extent = [min_lon, max_lon, min_lat, max_lat]

        # Plot map
        plt.imshow(map_img, extent=extent)

        plt.plot(lons, lats, linestyle='-', color='b', linewidth=2, label='Route')

        for loc in locations:
            plt.plot(loc['location'][0], loc['location'][1], marker='o', markersize=8, color='r')
            plt.text(loc['location'][0], loc['location'][1], loc['name'], fontsize=9, ha='right')

        plt.title('Route')
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

        # Ensure the static directory path is correct and create it if it doesn't exist
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)

        # Save the plot as an image file in the static directory
        plot_path = os.path.join(static_dir, 'route_plot.png')
        plt.savefig(plot_path, dpi=200)
        plt.close()

        return plot_path
    return None

# Function to get the next route_id
def get_next_route_id():
    cursor.execute("SELECT 'RID_' || TO_CHAR(NVL(MAX(TO_NUMBER(SUBSTR(route_id, 5))), 0) + 1) FROM delivery_route_history")
    return cursor.fetchone()[0]

# # Route for calculating the route based on database data
# @app.route('/calculate', methods=['POST'])
# def calculate():
#     # Fetch all locations from the database
#     cursor.execute("SELECT location, latitude, longitude, priority FROM location_info")
#     rows = cursor.fetchall()

#     locations = [
#         {"name": row[0], "location": [row[2], row[1]], "priority": row[3]} for row in rows
#     ]

#     if len(locations) < 2:
#         return jsonify({'error': 'Insufficient locations to calculate route.'})

#     # Sort locations by priority, using a default high number for None priorities
#     sorted_locations = sorted(locations, key=lambda x: x['priority'] if x['priority'] is not None else float('inf'))

#     start_location = sorted_locations[0]
#     end_location = sorted_locations[-1]
#     sorted_locations = sorted_locations[1:-1]

#     # Define start and end points
#     start = start_location['location']
#     end = end_location['location']

#     route_coordinates = calculate_route(start, end, sorted_locations, "5b3ce3597851110001cf6248cea24e90714e4a8c9e6b653486f0e396")

#     if route_coordinates:
#         plot_path = plot_route(route_coordinates, [start_location] + sorted_locations + [end_location])
#         if plot_path:
#             # Prepare the response data
#             order_of_locations = [start_location['name']] + [loc['name'] for loc in sorted_locations] + [end_location['name']]
#             distances = []
#             all_locations = [start_location] + sorted_locations + [end_location]
#             for i in range(len(all_locations) - 1):
#                 distance = calculate_distance(all_locations[i]['location'], all_locations[i+1]['location'])
#                 distances.append({
#                     'location_pair': f"{all_locations[i]['name']} --> {all_locations[i+1]['name']}",
#                     'distance': f"{distance:.2f} meters"
#                 })

#                 # Insert route details into delivery_route_history table
#                 route_id = get_next_route_id()
#                 first_point = start_location['name']
#                 final_point = end_location['name']
#                 route = ','.join(order_of_locations)
#                 route_date = datetime.now().date()
#                 route_time = datetime.now()

#                 try:
#                     cursor.execute("""
#                         INSERT INTO delivery_route_history (route_id, first_point, final_point, route, route_date, route_time)
#                         VALUES (:1, :2, :3, :4, :5, :6)
#                     """, (
#                         route_id,
#                         first_point,
#                         final_point,
#                         route,
#                         route_date,
#                         route_time
#                     ))
#                     connection.commit()
#                 except cx_Oracle.DatabaseError as e:
#                     connection.rollback()
#                     print(f"Database error: {e}")

#             return jsonify({
#                 'plot_path': url_for('static', filename='route_plot.png'),
#                 'order_of_locations': order_of_locations,
#                 'distances': distances  # Include distances in the response
#             })

@app.route('/calculate', methods=['POST'])
def calculate():
    # Fetch all locations from the database
    cursor.execute("SELECT location, latitude, longitude, priority FROM location_info")
    rows = cursor.fetchall()

    locations = [
        {"name": row[0], "location": [row[2], row[1]], "priority": row[3]} for row in rows
    ]

    if len(locations) < 2:
        return jsonify({'error': 'Insufficient locations to calculate route.'})

    # Sort locations by priority, using a default high number for None priorities
    sorted_locations = sorted(locations, key=lambda x: x['priority'] if x['priority'] is not None else float('inf'))

    start_location = sorted_locations[0]
    end_location = sorted_locations[-1]
    sorted_locations = sorted_locations[1:-1]

    # Define start and end points
    start = start_location['location']
    end = end_location['location']

    route_coordinates = calculate_route(start, end, sorted_locations, "5b3ce3597851110001cf6248cea24e90714e4a8c9e6b653486f0e396")

    if route_coordinates:
        plot_path = plot_route(route_coordinates, [start_location] + sorted_locations + [end_location])
        if plot_path:
            # Prepare the response data
            order_of_locations = [start_location['name']] + [loc['name'] for loc in sorted_locations] + [end_location['name']]
            distances = []
            all_locations = [start_location] + sorted_locations + [end_location]
            for i in range(len(all_locations) - 1):
                distance = calculate_distance(all_locations[i]['location'], all_locations[i+1]['location'])
                distances.append({
                    'location_pair': f"{all_locations[i]['name']} --> {all_locations[i+1]['name']}",
                    'distance': f"{distance:.2f} meters"
                })

            # Insert route details into delivery_route_history table
            route_id = get_next_route_id()
            first_point = start_location['name']
            final_point = end_location['name']
            route = ','.join(order_of_locations)
            route_date = datetime.now().date()
            route_time = datetime.now()

            try:
                cursor.execute("""
                    INSERT INTO delivery_route_history (route_id, first_point, final_point, route, route_date, route_time)
                    VALUES (:1, :2, :3, :4, :5, :6)
                """, (
                    route_id,
                    first_point,
                    final_point,
                    route,
                    route_date,
                    route_time
                ))
                connection.commit()
            except cx_Oracle.DatabaseError as e:
                connection.rollback()
                print(f"Database error: {e}")

            return jsonify({
                'plot_path': url_for('static', filename='route_plot.png'),
                'order_of_locations': order_of_locations,
                'distances': distances  # Include distances in the response
            })

    return jsonify({'error': 'Failed to calculate route.'})

# Haversine formula to calculate distance between two points
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # Radius of the Earth in meters
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)
    a = sin(delta_phi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(delta_lambda / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c  # Distance in meters
    return distance

# Function to find the two nearest drivers
def find_two_nearest_drivers(start_point, drivers):
    nearest_drivers = []
    # Sort the drivers by distance from the start point
    drivers.sort(key=lambda driver: haversine(start_point[0], start_point[1], driver['latitude'], driver['longitude']))
    # Take the two nearest drivers
    nearest_drivers = drivers[:2]
    return nearest_drivers

@app.route('/find_nearest_drivers', methods=['GET'])
def find_nearest_drivers():
    cursor.execute("SELECT driver_id, driver_name, location, latitude, longitude, mobile_no FROM drivers")
    drivers = cursor.fetchall()

    # Fetch the starting point from the database
    cursor.execute("SELECT latitude, longitude FROM location_info ORDER BY priority ASC FETCH FIRST 1 ROW ONLY")
    start_point = cursor.fetchone()
    if not start_point:
        return jsonify({'error': 'No starting point found.'})

    start_lat, start_lon = start_point[0], start_point[1]

    # Convert drivers to a list of dictionaries
    driver_list = [
        {
            'driver_id': driver[0],
            'driver_name': driver[1],
            'location': driver[2],
            'latitude': driver[3],
            'longitude': driver[4],
            'mobile_no': driver[5]
        }
        for driver in drivers
    ]

    # Find the two nearest drivers using the Nearest Neighbor algorithm with Haversine formula
    nearest_drivers = find_two_nearest_drivers((start_lat, start_lon), driver_list)

    if nearest_drivers:
        return jsonify({
            'nearest_drivers': nearest_drivers
        })
    else:
        return jsonify({'error': 'No drivers found.'})




"""-----------------------------------------------------------------------------------"""
"""                                 view_delivery page                                """
"""-----------------------------------------------------------------------------------"""
@app.route('/view_delivery_points')
def view_delivery_points():
    cursor.execute("SELECT store_name, mobile_number, location, latitude, longitude, priority FROM location_info")
    rows = cursor.fetchall()
    delivery_points = [
        {"store_name": row[0], "mobile_number": row[1], "location": row[2], "latitude": row[3], "longitude": row[4], "priority": row[5]}
        for row in rows
    ]
    return render_template('view_delivery_points.html', delivery_points=delivery_points)

"""-----------------------------------------------------------------------------------"""
"""                                  add_delivery page                                """
"""-----------------------------------------------------------------------------------"""
@app.route('/add_delivery_points')
def add_delivery_points():
    # Add logic for adding delivery points
    return render_template('add_delivery_points.html')


"""-----------------------------------------------------------------------------------"""
"""                                 Driver_dashboard                                  """
"""-----------------------------------------------------------------------------------"""

@app.route('/driver_dashboard')
def driver_dashboard():
    cursor.execute("SELECT driver_id, driver_name, location, latitude, longitude, mobile_no FROM drivers")
    rows = cursor.fetchall()
    drivers = [
        {"driver_id": row[0], "driver_name": row[1], "location": row[2], "mobile_no": row[5]}
        for row in rows
    ]
    return render_template('driver_dashboard.html', drivers=drivers)


@app.route('/add_driver', methods=['GET', 'POST'])
def add_driver():
    if request.method == 'POST':
        driver_id = request.form['driver_id']
        driver_name = request.form['driver_name']
        location = request.form['location']
        latitude = request.form['latitude']
        longitude = request.form['longitude']
        mobile_no = request.form['mobile_no']
        
        cursor.execute("""
            INSERT INTO drivers (driver_id, driver_name, location, latitude, longitude, mobile_no)
            VALUES (:driver_id, :driver_name, :location, :latitude, :longitude, :mobile_no)
        """, driver_id=driver_id, driver_name=driver_name, location=location, latitude=latitude, longitude=longitude, mobile_no=mobile_no)
        
        connection.commit()
        return redirect(url_for('driver_dashboard'))
    
    return render_template('add_driver.html')

@app.route('/delete_driver', methods=['POST'])
def delete_driver():
    if request.method == 'POST':
        driver_id = request.form['driver_id']
        driver_name = request.form['driver_name']

        cursor.execute("DELETE FROM drivers WHERE driver_id = :driver_id AND driver_name = :driver_name", 
                        {'driver_id': driver_id, 'driver_name': driver_name})
        connection.commit()
        return redirect(url_for('driver_dashboard'))


"""-----------------------------------------------------------------------------------"""
"""                                 History - page                                    """
"""-----------------------------------------------------------------------------------"""
@app.route('/history')
def history():
    try:
        # Establish the database connection
        cursor = connection.cursor()

        # Fetching delivery points
        cursor.execute("SELECT route_id, route_date, route_time, first_point, final_point, route FROM delivery_route_history")
        delivery_points = cursor.fetchall()

        delivery_points_data = [
            {
                'route_id': row[0],
                'route_date': row[1],
                'route_time': row[2],
                'first_point': row[3],
                'final_point': row[4],
                'route': row[5].read()  # Convert CLOB to string
            } for row in delivery_points
        ]
        print("Delivery points data:", delivery_points_data)

        # Fetching the routes for top 3 delivery locations
        cursor.execute("SELECT route FROM delivery_route_history")
        routes = cursor.fetchall()

        # Process the route data to count occurrences of each location
        location_counts = {}
        for route in routes:
            locations = route[0].read().split(',')  # Convert CLOB to string and then split
            for location in locations:
                location = location.strip()  # Remove any leading/trailing whitespace
                if location in location_counts:
                    location_counts[location] += 1
                else:
                    location_counts[location] = 1

        # Find the top 3 most frequent locations
        top_locations = sorted(location_counts.items(), key=lambda item: item[1], reverse=True)[:3]

        top_locations_data = [
            {
                'location_name': location,
                'delivery_count': count
            } for location, count in top_locations
        ]
        print("Top locations data:", top_locations_data)
        
        # Close the cursor and connection
        
    except cx_Oracle.DatabaseError as e:
        print(f"Database error: {e}")
        delivery_points_data = []
        top_locations_data = []

    return render_template('history.html', delivery_points=delivery_points_data, top_locations=top_locations_data)



"""-----------------------------------------------------------------------------------"""
"""                                 About us -page                                    """
"""-----------------------------------------------------------------------------------"""
@app.route('/about_us')
def about_us():
    # Add logic for about us page
    return render_template('about_us.html')

if __name__ == '__main__':
    app.run(debug=True)

