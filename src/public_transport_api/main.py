from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

from controllers.departures_controller import departures_bp
from controllers.trips_controller import trips_bp


app = Flask(__name__)
DATABASE = '../../trips.sqlite'

CORS(app)

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/public_transport/city/<city>/closest_departures', methods=['GET'])
def closest_departures(city):
    # Example: ?stop_id=123&destination=456
    stop_id = request.args.get('stop_id')
    destination = request.args.get('destination')
    conn = get_db_connection()
    cursor = conn.cursor()
    # This query should be adapted to your schema
    cursor.execute('''
        SELECT * FROM departures WHERE city=? AND stop_id=? AND destination=? ORDER BY departure_time ASC LIMIT 5
    ''', (city, stop_id, destination))
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