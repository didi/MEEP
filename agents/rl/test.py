import unittest

from utils import flatten_variables


class FlattenVariablesTest(unittest.TestCase):
    def test_find_place_error(self):
        response = {
            'variable_group': 'v1',
            'variable_group_api_call': "find_place('I', '0', '1')",
            'variables': [
                {'full_name': 'v1_error', 'name': 'error',
                    'value': 'No places could be found matching i. See microworld_map.txt for a list of places'}
            ]
        }
        variables = flatten_variables(response)
        self.assertEqual(len(variables), 1)

    def test_find_place_success(self):
        response = {
            'variable_group': 'v1',
            'variable_group_api_call': "find_place('Starbucks', '0', '1')",
            'variables': [
                {'full_name': 'v1_name', 'name': 'name', 'value': 'Starbucks'},
                {'full_name': 'v1_address', 'name': 'address',
                    'value': '3 Main Street, Marina del Rey, CA'},
                {'full_name': 'v1_address_simple',
                 'name': 'address_simple',
                 'value': '3 Main Street'},
                {'full_name': 'v1_latitude', 'name': 'latitude', 'value': '2'},
                {'full_name': 'v1_longitude', 'name': 'longitude', 'value': '3'},
                {'name': 'types', 'value': [
                    {'full_name': 'v1_types_0', 'name': 0, 'value': 'cafe'},
                    {'full_name': 'v1_types_1', 'name': 1, 'value': 'starbucks'},
                    {'full_name': 'v1_types_2', 'name': 2, 'value': 'coffee'}
                ]},
                {'full_name': 'v1_rating', 'name': 'rating', 'value': '2'},
                {'full_name': 'v1_distance', 'name': 'distance', 'value': '4.0 mins'},
                {'full_name': 'v1_duration', 'name': 'duration', 'value': '4.0 mi'},
                {'full_name': 'v1_neighborhood',
                 'name': 'neighborhood',
                 'value': 'Marina del Rey'},
                {'full_name': 'v1_locality',
                 'name': 'locality',
                 'value': 'Los Angeles'},
                {'full_name': 'v1_is_open', 'name': 'is_open', 'value': 'True'}
            ]
        }
        variables = flatten_variables(response)
        self.assertEqual(len(variables), 14)

    def test_places_nearby_error(self):
        response = {
            'variable_group': 'v1',
            'variable_group_api_call': "places_nearby('I', '0', '1')",
            'variables': []
        }
        variables = flatten_variables(response)
        self.assertEqual(len(variables), 0)

    def test_places_nearby_one_place(self):
        response = {
            'variable_group': 'v4',
            'variable_group_api_call': "places_nearby('Starbucks', '0', '1')",
            'variables': [
                {'name': '0', 'value': [
                    {'full_name': 'v4_0_name', 'name': 'name', 'value': 'Starbucks'},
                    {'full_name': 'v4_0_address', 'name': 'address',
                        'value': '3 Main Street, Marina del Rey, CA'},
                    {'full_name': 'v4_0_address_simple',
                        'name': 'address_simple', 'value': '3 Main Street'},
                    {'full_name': 'v4_0_latitude', 'name': 'latitude', 'value': '2'},
                    {'full_name': 'v4_0_longitude',
                        'name': 'longitude', 'value': '3'},
                    {'name': 'types', 'value': [
                        {'full_name': 'v4_0_types_0', 'name': 0, 'value': 'cafe'},
                        {'full_name': 'v4_0_types_1',
                            'name': 1, 'value': 'starbucks'},
                        {'full_name': 'v4_0_types_2', 'name': 2, 'value': 'coffee'}
                    ]},
                    {'full_name': 'v4_0_rating', 'name': 'rating', 'value': '2'},
                    {'full_name': 'v4_0_distance',
                        'name': 'distance', 'value': '4.0 mins'},
                    {'full_name': 'v4_0_duration',
                        'name': 'duration', 'value': '4.0 mi'},
                    {'full_name': 'v4_0_neighborhood',
                        'name': 'neighborhood', 'value': 'Marina del Rey'},
                    {'full_name': 'v4_0_locality',
                        'name': 'locality', 'value': 'Los Angeles'},
                    {'full_name': 'v4_0_is_open', 'name': 'is_open', 'value': 'True'}
                ]}
            ]
        }
        variables = flatten_variables(response)
        self.assertEqual(len(variables), 14)

    def test_places_nearby_three_places(self):
        response = {
            'variable_group': 'v3',
            'variable_group_api_call': "places_nearby('Starbucks', '0', '1')",
            'variables': [
                {'name': '0', 'value': [
                    {'full_name': 'v3_0_name', 'name': 'name', 'value': 'Starbucks'},
                    {'full_name': 'v3_0_address', 'name': 'address',
                        'value': '3 Main Street, Marina del Rey, CA'},
                    {'full_name': 'v3_0_address_simple',
                        'name': 'address_simple', 'value': '3 Main Street'},
                    {'full_name': 'v3_0_latitude', 'name': 'latitude', 'value': '1'},
                    {'full_name': 'v3_0_longitude',
                        'name': 'longitude', 'value': '3'},
                    {'name': 'types', 'value': [
                        {'full_name': 'v3_0_types_0', 'name': 0, 'value': 'cafe'},
                        {'full_name': 'v3_0_types_1',
                            'name': 1, 'value': 'starbucks'},
                        {'full_name': 'v3_0_types_2', 'name': 2, 'value': 'coffee'}
                    ]},
                    {'full_name': 'v3_0_rating', 'name': 'rating', 'value': '2'},
                    {'full_name': 'v3_0_distance',
                        'name': 'distance', 'value': '3.0 mins'},
                    {'full_name': 'v3_0_duration',
                        'name': 'duration', 'value': '3.0 mi'},
                    {'full_name': 'v3_0_neighborhood',
                        'name': 'neighborhood', 'value': 'Marina del Rey'},
                    {'full_name': 'v3_0_locality',
                        'name': 'locality', 'value': 'Los Angeles'},
                    {'full_name': 'v3_0_is_open', 'name': 'is_open', 'value': 'True'}
                ]},
                {'name': '1', 'value': [
                    {'full_name': 'v3_1_name', 'name': 'name',
                        'value': 'Starbucks-Deluxe'},
                    {'full_name': 'v3_1_address', 'name': 'address',
                        'value': '5 Main Street, Marina del Rey, CA'},
                    {'full_name': 'v3_1_address_simple',
                        'name': 'address_simple', 'value': '5 Main Street'},
                    {'full_name': 'v3_1_latitude', 'name': 'latitude', 'value': '1'},
                    {'full_name': 'v3_1_longitude',
                        'name': 'longitude', 'value': '5'},
                    {'name': 'types', 'value': [
                        {'full_name': 'v3_1_types_0', 'name': 0, 'value': 'cafe'},
                        {'full_name': 'v3_1_types_1',
                            'name': 1, 'value': 'starbucks'},
                        {'full_name': 'v3_1_types_2', 'name': 2, 'value': 'coffee'},
                        {'full_name': 'v3_1_types_3', 'name': 3, 'value': 'deluxe'}
                    ]},
                    {'full_name': 'v3_1_rating', 'name': 'rating', 'value': '4'},
                    {'full_name': 'v3_1_distance',
                        'name': 'distance', 'value': '5.0 mins'},
                    {'full_name': 'v3_1_duration',
                        'name': 'duration', 'value': '5.0 mi'},
                    {'full_name': 'v3_1_neighborhood',
                        'name': 'neighborhood', 'value': 'Marina del Rey'},
                    {'full_name': 'v3_1_locality',
                        'name': 'locality', 'value': 'Los Angeles'},
                    {'full_name': 'v3_1_is_open', 'name': 'is_open', 'value': 'True'}
                ]},
                {'name': '2', 'value': [
                    {'full_name': 'v3_2_name', 'name': 'name', 'value': 'Starbucks'},
                    {'full_name': 'v3_2_address', 'name': 'address',
                        'value': '11 Main Street, Venice, CA'},
                    {'full_name': 'v3_2_address_simple',
                        'name': 'address_simple', 'value': '11 Main Street'},
                    {'full_name': 'v3_2_latitude', 'name': 'latitude', 'value': '1'},
                    {'full_name': 'v3_2_longitude',
                        'name': 'longitude', 'value': '11'},
                    {'name': 'types', 'value': [
                        {'full_name': 'v3_2_types_0', 'name': 0, 'value': 'cafe'},
                        {'full_name': 'v3_2_types_1',
                            'name': 1, 'value': 'starbucks'},
                        {'full_name': 'v3_2_types_2', 'name': 2, 'value': 'coffee'}
                    ]},
                    {'full_name': 'v3_2_rating', 'name': 'rating', 'value': '3'},
                    {'full_name': 'v3_2_distance',
                        'name': 'distance', 'value': '11.0 mins'},
                    {'full_name': 'v3_2_duration',
                        'name': 'duration', 'value': '11.0 mi'},
                    {'full_name': 'v3_2_neighborhood',
                        'name': 'neighborhood', 'value': 'Venice'},
                    {'full_name': 'v3_2_locality',
                        'name': 'locality', 'value': 'Los Angeles'},
                    {'full_name': 'v3_2_is_open', 'name': 'is_open', 'value': 'True'}
                ]
                }]
        }
        variables = flatten_variables(response)
        self.assertEqual(len(variables), 43)


if __name__ == '__main__':
    unittest.main()
