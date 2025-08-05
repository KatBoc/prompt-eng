import sqlite3
import math
import datetime


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
                    "distance_start_to_stop": dist
                })

        # Filter departures by direction and format times
        filtered_departures = []
        for dep in departures:
            # Get the full stop sequence for the trip
            cursor.execute("""
                SELECT st.stop_id, s.stop_lat, s.stop_lon
                FROM stop_times st
                JOIN stops s ON st.stop_id = s.stop_id
                WHERE st.trip_id = ?
                ORDER BY st.stop_sequence ASC
            """, (dep['trip_id'],))
            trip_stops = cursor.fetchall()
            # Find indices of departure stop and closest stop to destination
            dep_idx = None
            dest_idx = None
            min_dest_dist = float('inf')
            for i, ts in enumerate(trip_stops):
                if ts['stop_id'] == dep['stop']['id']:
                    dep_idx = i
                dest_dist = haversine_distance(ts['stop_lat'], ts['stop_lon'], end_lat, end_lon)
                if dest_dist < min_dest_dist:
                    min_dest_dist = dest_dist
                    dest_idx = i
            # Only include departures where the trip moves towards the destination
            if dep_idx is not None and dest_idx is not None and dep_idx < dest_idx:
                # Format departure time as ISO 8601 (assume today)
                today = datetime.date.today().isoformat()
                dep_time_iso = f"{today}T{dep['stop']['departure_time']}Z"
                filtered_departures.append({
                    "trip_id": dep['trip_id'],
                    "route_id": dep['route_id'],
                    "trip_headsign": dep['trip_headsign'],
                    "stop": {
                        "name": dep['stop']['name'],
                        "coordinates": dep['stop']['coordinates'],
                        "arrival_time": dep_time_iso,  # No arrival_time in current query
                        "departure_time": dep_time_iso
                    }
                })
        # Sort by distance and apply global limit
        filtered_departures = sorted(filtered_departures, key=lambda x: haversine_distance(start_lat, start_lon, x['stop']['coordinates']['latitude'], x['stop']['coordinates']['longitude']))[:limit]
        return filtered_departures
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []
    finally:
        if conn:
            conn.close()
