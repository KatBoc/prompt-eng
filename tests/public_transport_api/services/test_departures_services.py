import unittest
from unittest.mock import patch, MagicMock
from public_transport_api.services.departures_service import get_closest_departures


class TestDeparturesService(unittest.TestCase):
    @patch('public_transport_api.services.departures_service.sqlite3.connect')
    def test_get_closest_departures_success(self, mock_connect):
        # Mock connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.row_factory = None

        # Mock stops within 1km
        mock_cursor.fetchall.side_effect = [
            [
                {'stop_id': 'stop1', 'stop_name': 'Stop 1', 'stop_lat': 51.1, 'stop_lon': 17.03},
                {'stop_id': 'stop2', 'stop_name': 'Stop 2', 'stop_lat': 51.11, 'stop_lon': 17.04}
            ],
            # Mock departures for stop1
            [
                {'trip_id': 'tripA', 'departure_time': '08:30:00', 'route_id': 'A', 'trip_headsign': 'HeadA'}
            ],
            # Mock departures for stop2
            [
                {'trip_id': 'tripB', 'departure_time': '08:35:00', 'route_id': 'B', 'trip_headsign': 'HeadB'}
            ],
            # Mock trip stops for tripA
            [
                {'stop_id': 'stop1', 'stop_lat': 51.1, 'stop_lon': 17.03},
                {'stop_id': 'stop2', 'stop_lat': 51.11, 'stop_lon': 17.04}
            ],
            # Mock trip stops for tripB
            [
                {'stop_id': 'stop2', 'stop_lat': 51.11, 'stop_lon': 17.04},
                {'stop_id': 'stop1', 'stop_lat': 51.1, 'stop_lon': 17.03}
            ]
        ]

        # Call the function
        result = get_closest_departures('51.1000,17.0300', '51.1100,17.0400', '2025-04-02T08:30:00Z', limit=2)
        # Check result format and content
        self.assertIsInstance(result, list)
        self.assertGreaterEqual(len(result), 1)
        for dep in result:
            self.assertIn('trip_id', dep)
            self.assertIn('route_id', dep)
            self.assertIn('trip_headsign', dep)
            self.assertIn('stop', dep)
            self.assertIn('name', dep['stop'])
            self.assertIn('coordinates', dep['stop'])
            self.assertIn('departure_time', dep['stop'])
            self.assertTrue(dep['stop']['departure_time'].endswith('Z'))

    @patch('public_transport_api.services.departures_service.sqlite3.connect')
    def test_get_closest_departures_no_stops(self, mock_connect):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.row_factory = None
        # No stops found
        mock_cursor.fetchall.side_effect = [[], [], [], [], []]
        result = get_closest_departures('51.1000,17.0300', '51.1100,17.0400', '2025-04-02T08:30:00Z', limit=2)
        self.assertEqual(result, [])

    @patch('public_transport_api.services.departures_service.sqlite3.connect')
    def test_get_closest_departures_invalid_coords(self, mock_connect):
        result = get_closest_departures('invalid', 'invalid', '2025-04-02T08:30:00Z', limit=2)
        self.assertEqual(result, [])

    @patch('public_transport_api.services.departures_service.sqlite3.connect')
    def test_get_closest_departures_db_error(self, mock_connect):
        mock_connect.side_effect = Exception('DB error')
        result = get_closest_departures('51.1000,17.0300', '51.1100,17.0400', '2025-04-02T08:30:00Z', limit=2)
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()
