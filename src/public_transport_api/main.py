from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import math

from controllers.departures_controller import departures_bp
from controllers.trips_controller import trips_bp


app = Flask(__name__)
DATABASE = '../../trips.sqlite'

CORS(app)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 1000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))  # meters

# Helper to find nearest stop
def find_nearest_stop(conn, lat, lon):
    cursor = conn.cursor()
    cursor.execute('SELECT stop_id, stop_name, stop_lat, stop_lon FROM stops')
    stops = cursor.fetchall()
    min_dist = float('inf')
    nearest = None
    for stop in stops:
        dist = haversine(lat, lon, float(stop['stop_lat']), float(stop['stop_lon']))
        if dist < min_dist:
            min_dist = dist
            nearest = stop
    return nearest

@app.route('/public_transport/city/<city>/closest_departures', methods=['GET'])
def closest_departures(city):
    # Accept coordinates or stop_id
    start_lat = request.args.get('start_lat', type=float)
    start_lng = request.args.get('start_lng', type=float)
    stop_id = request.args.get('stop_id')
    destination = request.args.get('destination')
    conn = get_db_connection()
    if start_lat and start_lng:
        nearest_stop = find_nearest_stop(conn, start_lat, start_lng)
        if not nearest_stop:
            conn.close()
            return jsonify([])
        stop_id = nearest_stop['stop_id']
    cursor = conn.cursor()
    if stop_id and destination:
        cursor.execute('''
            SELECT * FROM departures WHERE city=? AND stop_id=? AND destination=? ORDER BY departure_time ASC LIMIT 5
        ''', (city, stop_id, destination))
    elif stop_id:
        cursor.execute('''
            SELECT * FROM departures WHERE city=? AND stop_id=? ORDER BY departure_time ASC LIMIT 5
        ''', (city, stop_id))
    else:
        conn.close()
        return jsonify([])
    departures = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(departures)

@app.route('/public_transport/city/<city>/trip/<trip_id>', methods=['GET'])
def trip_details(city, trip_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    # This query should be adapted to your schema
    cursor.execute('''
        SELECT * FROM trips WHERE city=? AND trip_id=?
    ''', (city, trip_id))
    trip = cursor.fetchone()
    conn.close()
    if trip:
        return jsonify(dict(trip))
    else:
        return jsonify({'error': 'Trip not found'}), 404


app.register_blueprint(departures_bp)
app.register_blueprint(trips_bp)


@app.route("/")
def index():
    return "Welcome to the Public Transport API for Wrocław!"

if __name__ == "__main__":
    app.run(debug=True, port=5001)