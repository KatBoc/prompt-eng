import sqlite3
import math


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def get_closest_departures(start_coordinates, end_coordinates, start_time, limit=5):
    # Parse coordinates
    try:
        start_lat, start_lon = map(float, start_coordinates.split(','))
        end_lat, end_lon = map(float, end_coordinates.split(','))
    except Exception:
        return []

    conn = None
    try:
        conn = sqlite3.connect("trips.sqlite")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Find stops within 1km of start
        cursor.execute("SELECT stop_id, stop_name, stop_lat, stop_lon FROM stops")
        stops = cursor.fetchall()
        nearby_stops = []
        for stop in stops:
            dist = haversine_distance(start_lat, start_lon, stop['stop_lat'], stop['stop_lon'])
            if dist <= 1000:
                nearby_stops.append((stop, dist))
        nearby_stops = sorted(nearby_stops, key=lambda x: x[1])[:limit]

        departures = []
        for stop, dist in nearby_stops:
            # Find upcoming departures for this stop
            cursor.execute("""
                SELECT st.trip_id, st.departure_time, t.route_id, t.trip_headsign
                FROM stop_times st
                JOIN trips t ON st.trip_id = t.trip_id
                WHERE st.stop_id = ? AND st.departure_time >= ?
                ORDER BY st.departure_time ASC
                LIMIT 3
            """, (stop['stop_id'], start_time[11:19]))  # Use only HH:MM:SS
            for row in cursor.fetchall():
                debug_dist_stop_to_end = haversine_distance(stop['stop_lat'], stop['stop_lon'], end_lat, end_lon)
                departures.append({
                    "trip_id": row['trip_id'],
                    "route_id": row['route_id'],
                    "trip_headsign": row['trip_headsign'],
                    "stop": {
                        "id": stop['stop_id'],
                        "name": stop['stop_name'],
                        "coordinates": {
                            "latitude": float(stop['stop_lat']),
                            "longitude": float(stop['stop_lon'])
                        },
                        "departure_time": row['departure_time']
                    },
                    "distance_start_to_stop": dist,
                    "debug_dist_stop_to_end": debug_dist_stop_to_end
                })
        return departures
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []
    finally:
        if conn:
            conn.close()
