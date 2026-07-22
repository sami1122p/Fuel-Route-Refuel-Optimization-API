import json
from django.test import TestCase, Client
from django.urls import reverse

from .services.geocoding import geocode_location, parse_lat_lon
from .services.routing import fetch_osrm_route
from .services.fuel_optimizer import optimize_fuel_stops, compute_cumulative_distances

class GeocodingServiceTest(TestCase):
    def test_parse_lat_lon(self):
        result = parse_lat_lon("40.7128,-74.0060")
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result[0], 40.7128)
        self.assertAlmostEqual(result[1], -74.0060)

    def test_preset_lookup(self):
        lat, lon, addr = geocode_location("New York, NY")
        self.assertAlmostEqual(lat, 40.712776)
        self.assertAlmostEqual(lon, -74.005974)
        self.assertIn("New York", addr)

    def test_empty_query_raises_value_error(self):
        with self.assertRaises(ValueError):
            geocode_location("")

class RoutingServiceTest(TestCase):
    def test_fetch_osrm_route_valid(self):
        # Route from NYC to Philadelphia (~95 miles)
        start_lat, start_lon = 40.7128, -74.0060
        finish_lat, finish_lon = 39.9526, -75.1652
        
        result = fetch_osrm_route(start_lat, start_lon, finish_lat, finish_lon)
        self.assertIn('distance_miles', result)
        self.assertGreater(result['distance_miles'], 80)
        self.assertLess(result['distance_miles'], 120)
        self.assertIn('route_latlon', result)
        self.assertGreater(len(result['route_latlon']), 10)

class FuelOptimizerTest(TestCase):
    def test_short_trip_no_fuel_stop(self):
        # Short trip under 500 miles (NYC to Philly ~95 miles)
        route_latlon = [[40.7128, -74.0060], [40.0, -74.5], [39.9526, -75.1652]]
        opt = optimize_fuel_stops(route_latlon, total_distance_miles=95.0)
        self.assertEqual(opt['fuel_stops_count'], 0)
        self.assertEqual(opt['total_fuel_cost_usd'], 0.0)
        self.assertAlmostEqual(opt['total_trip_gallons_required'], 9.5)

    def test_long_trip_multiple_fuel_stops(self):
        # Long trip NY to LA (~2800 miles)
        start_lat, start_lon = 40.7128, -74.0060
        finish_lat, finish_lon = 34.0522, -118.2437
        route_data = fetch_osrm_route(start_lat, start_lon, finish_lat, finish_lon)
        
        opt = optimize_fuel_stops(route_data['route_latlon'], route_data['distance_miles'])
        self.assertGreater(opt['fuel_stops_count'], 3)
        self.assertGreater(opt['total_fuel_cost_usd'], 400.0)
        self.assertIn('fuel_stops', opt)
        
        # Verify structure of fuel stops
        stop = opt['fuel_stops'][0]
        self.assertIn('station_id', stop)
        self.assertIn('name', stop)
        self.assertIn('price_per_gallon', stop)
        self.assertIn('fuel_cost_usd', stop)

class RouteFuelAPIViewTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_missing_parameters_returns_400(self):
        response = self.client.get('/api/route/?start=New+York,+NY')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')

    def test_valid_route_api_call(self):
        response = self.client.get('/api/route/?start=New+York,+NY&finish=Los+Angeles,+CA')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['status'], 'success')
        self.assertIn('summary', data)
        self.assertGreater(data['summary']['total_distance_miles'], 2500)
        self.assertGreater(data['summary']['fuel_stops_count'], 3)
        self.assertIn('fuel_stops', data)
        self.assertIn('geojson', data)
        self.assertEqual(data['geojson']['type'], 'FeatureCollection')

    def test_map_interface_renders_200(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fuel Route Planner')
