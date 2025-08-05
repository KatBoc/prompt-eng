from flask import Blueprint, jsonify, request
from datetime import datetime
from public_transport_api.services.departures_service import get_closest_departures

departures_bp = Blueprint('departures', __name__)

@departures_bp.route('/public_transport/city/<city>/closest_departures', methods=['GET'])
def closest_departures(city):
    # Validate city
    if city.lower() != 'wroclaw':
        return jsonify({'error': 'City not supported'}), 404

    # Parse query parameters
    start_coordinates = request.args.get('start_coordinates')
    end_coordinates = request.args.get('end_coordinates')
    start_time = request.args.get('start_time', datetime.utcnow().isoformat() + 'Z')
    limit = request.args.get('limit', 5)
    try:
        limit = int(limit)
    except ValueError:
        return jsonify({'error': 'Invalid limit'}), 400

    # Validate required params
    if not start_coordinates or not end_coordinates:
        return jsonify({'error': 'Missing required parameters'}), 400

    # Call service
    departures = get_closest_departures(start_coordinates, end_coordinates, start_time, limit)

    # Build metadata
    metadata = {
        'self': request.path + '?' + request.query_string.decode(),
        'city': city,
        'query_parameters': {
            'start_coordinates': start_coordinates,
            'end_coordinates': end_coordinates,
            'start_time': start_time,
            'limit': limit
        }
    }
    return jsonify({'metadata': metadata, 'departures': departures})
