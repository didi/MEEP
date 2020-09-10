import csv
import random
import os
from collections import namedtuple
from functools import partial
from rapidfuzz import fuzz
from apis.maps.maps_provider import MapsProvider

Place = namedtuple('Place', ['lat', 'lng', 'name', 'rating', 'price', 'types'])


class MicroworldMapProvider(MapsProvider):
    def __init__(self, *, map_path='microworld_map.txt'):
        self.places_path = os.path.join(os.path.dirname(__file__), map_path)

        with open(self.places_path) as fh:
            reader = csv.reader(
                filter(
                    lambda line: line.strip() and not line.startswith('#'), fh))
            self.places = [self._read_line(row) for row in reader]

    # Helpers
    def _read_line(self, row: list):
        '''Read static file into a Place object'''
        lat, lng, name, rating, price, *types = (x.strip() for x in row)
        return Place(lat, lng, name, rating, price, types)

    @staticmethod
    def _dist(src_lat, src_lng, dest_lat, dest_lng):
        return abs(float(src_lat) - float(dest_lat)) + \
            abs(float(src_lng) - float(dest_lng))

    def _query_matches(self, query: str, place: Place) -> bool:
        '''Test if query matches place.'''
        return (fuzz.partial_ratio(query, place.name.lower()) > 80
                or any(fuzz.token_sort_ratio(query, type_) > 80 for type_ in place.types)
                )

    def get_matching_places(self, query: str):
        '''Get a list of most relevant places. First try matching the whole string, then try matching words, then give up'''

        # Try matching the whole string
        matching_places = [
            p for p in self.places if self._query_matches(
                query, p)]
        if matching_places:
            return matching_places

        # Try matching individual words from the query
        matching_places = [
            p for p in self.places if any(
                self._query_matches(
                    word, p) for word in query.split())]
        return matching_places

    @staticmethod
    def _place_to_response(p: Place, src_lat: str, src_lng: str):
        '''convert a Place, `p`, to the format expected by the api'''
        dist = MicroworldMapProvider._dist(src_lat, src_lng, p.lat, p.lng)

        if int(p.lat) <= 5 and int(p.lng) <= 5:
            city = 'Marina del Rey'
        elif int(p.lat) <= 5 and int(p.lng) > 5:
            city = 'Santa Monica'
        elif int(p.lat) > 5 and int(p.lng) <= 5:
            city = 'Culver City'
        elif int(p.lat) > 5 and int(p.lng) > 5:
            city = 'Sawtelle'
        else:
            city = 'Los Angeles'

        street_names = [
            'First',
            'Second',
            'Third',
            'Fourth',
            'Fifth',
            'Sixth',
            'Seventh',
            'Eighth',
            'Ninth',
            'Tenth']

        return [
            {'name': 'name', 'value': p.name},
            {'name': 'address_simple',
             'value': street_names[min(len(street_names) - 1, int(p.lng) - 1)] + ' Street'},
            {'name': 'latitude', 'value': p.lat},
            {'name': 'longitude', 'value': p.lng},
            {'name': 'types', 'value': [
                {'name': i, 'value': type_} for i, type_ in enumerate(p.types)
            ]},
            {'name': 'rating', 'value': p.rating},
            {'name': 'price', 'value': p.price},
            {'name': 'distance', 'value': '{} mi'.format(dist)},
            {'name': 'duration', 'value': '{} mins'.format(dist)},
            {'name': 'neighborhood', 'value': city},
        ]

    # Main functions
    def distance_matrix(self, source_latitude, source_longitude,
                        destination_latitude, destination_longitude):
        try:
            dist = self._dist(
                source_latitude,
                source_longitude,
                destination_latitude,
                destination_longitude)
        except ValueError:
            return []
        return [
            {'name': 'distance', 'value': '{} mi'.format(dist)},
            {'name': 'duration', 'value': '{} mins'.format(dist)},
        ]

    def find_place(self, query, latitude, longitude):
        '''
        Return the place that contains query and is closest to latitude longitude
        Google maps does something more complicated to find the best (but not always closest) match
        '''
        query = query.strip().lower()
        matching_places = self.get_matching_places(query)

        if matching_places:
            closest_place = min(matching_places,
                                key=lambda place: self._dist(latitude, longitude, place.lat, place.lng))
            return self._place_to_response(closest_place, latitude, longitude)
        else:
            # no matching places
            raise ValueError(
                'No places could be found matching {}. See {} for a list of places'.format(query, self.places_path))

    def places_nearby(self, query, latitude, longitude):
        query = query.strip().lower()
        matching_places = self.get_matching_places(query)

        if matching_places:
            return [{'name': str(i), 'value': self._place_to_response(place, latitude, longitude)}
                    for i, place in enumerate(sorted(matching_places, key=lambda place: self._dist(latitude, longitude, place.lat, place.lng))[:3])
                    ]
        else:
            raise ValueError(
                'No places could be found matching {}. See {} for a list of places'.format(query, self.places_path))

    def generate_place(self, _source_latitude, _source_longitude):
        place = random.choice(self.places)
        response = self._place_to_response(place, _source_latitude, _source_longitude)
        return {
            "name": "destination",
            "value": [ kv for kv in response if kv["name"] in ("address_simple", "name", "latitude", "longitude") ]
        }

    def start_driving_no_map(self, latitude, longitude):
        return [{'name': 'success', 'value': True}]

    def start_driving(self, latitude, longitude, place_id):
        return self.start_driving_no_map(latitude, longitude)


class MicroworldMapProvider2(MicroworldMapProvider):
    @staticmethod
    def _place_to_response(p: Place, src_lat: str, src_lng: str):
        '''convert a Place, `p`, to the format expected by the api'''
        dist = MicroworldMapProvider2._dist(src_lat, src_lng, p.lat, p.lng)

        if float(p.lat) <= 5 and float(p.lng) <= 5:
            city = 'Marina del Rey'
        elif float(p.lat) <= 5 and float(p.lng) > 5:
            city = 'Santa Monica'
        elif float(p.lat) > 5 and float(p.lng) <= 5:
            city = 'Culver City'
        elif float(p.lat) > 5 and float(p.lng) > 5:
            city = 'Sawtelle'
        else:
            city = 'Los Angeles'

        street_names = [
            'First',
            'Second',
            'Third',
            'Fourth',
            'Fifth',
            'Sixth',
            'Seventh',
            'Eighth',
            'Ninth',
            'Tenth']

        try:
            streetname = street_names[int(p.lng) - 1] + ' Street'
            address = p.lat + ' ' + streetname
        except ValueError:
            streetname = ''
            address = ''

        result = [
            {'name': 'name', 'value': p.name},
            {'name': 'address_simple', 'value': address},
            {'name': 'streetname', 'value': streetname},
            {'name': 'latitude', 'value': p.lat},
            {'name': 'longitude', 'value': p.lng},
            {'name': 'types', 'value': [
                {'name': i, 'value': type_} for i, type_ in enumerate(p.types)
            ]},
            {'name': 'rating', 'value': p.rating},
            {'name': 'price', 'value': p.price},
            {'name': 'distance', 'value': '{} mi'.format(dist)},
            {'name': 'duration', 'value': '{} mins'.format(dist)},
            {'name': 'neighborhood', 'value': city},
        ]

        # remove blank values
        result = [variable for variable in result if variable['value']]
        return result
