import logging
import random

import googlemaps
from apis.maps.maps_provider import MapsProvider
from apis.utils import add_variable_if_exists


class GoogleMapsProvider(MapsProvider):
    PLACE_QUERIES = [
        "barber shop",
        "drug store",
        "movie theater",
        "grocery store",
        "cafe",
        "restaurant"]

    def __init__(self, api_key):
        self.api_key = api_key
        self.gmaps = googlemaps.Client(key=api_key)
        self.units = 'imperial'

    def find_place(self, query, latitude, longitude):
        api_res = self.gmaps.find_place(
            input=query,
            input_type='textquery',
            fields=[
                'formatted_address',
                'name',
                'geometry',
                'place_id',
                'price_level',
                'types',
                'rating',
                'opening_hours'],
            location_bias="point:{},{}".format(
                latitude,
                longitude))
        if api_res['status'] == 'ZERO_RESULTS':
            return []

        place = api_res['candidates'][0]
        logging.debug(
            "FIND_PLACE (query = {}, latitude = {}, longitude= {}): {}".format(
                query, latitude, longitude, place))

        v = []
        add_variable_if_exists(v, place, 'name', ('name',))
        add_variable_if_exists(v, place, 'address', ('formatted_address',))
        add_variable_if_exists(
            v, place, 'latitude', ('geometry', 'location', 'lat',))
        add_variable_if_exists(
            v, place, 'longitude', ('geometry', 'location', 'lng',))
        add_variable_if_exists(v, place, 'price_level', ('price_level',))
        add_variable_if_exists(v, place, 'types', ('types',))
        add_variable_if_exists(v, place, 'rating', ('rating',))
        add_variable_if_exists(
            v, place, 'is_open', ('opening_hours', 'open_now',))

        for place_details_variable in self._place_details(place['place_id']):
            if not any(var['name'] == place_details_variable['name']
                       for var in v):
                v.append(place_details_variable)
        for distance_matrix_variable in self.distance_matrix(
                latitude, longitude, place['geometry']['location']['lat'], place['geometry']['location']['lng']):
            if not any(var['name'] == distance_matrix_variable['name']
                       for var in v):
                v.append(distance_matrix_variable)
        add_variable_if_exists(v, place, 'place_id', ('place_id',))
        return v

    def find_latlon(self, query, latlon):
        '''Just get the latitude and longitude of a place
        and some administrative details to make sure it's the right one.
        (Venice, CA, USA vs Venice, Italy)
        '''
        api_res = self.gmaps.find_place(
            input=query,
            input_type='textquery',
            fields=[
                'formatted_address',
                'name',
                'geometry',
                'place_id'],
            location_bias="point:" +
            latlon)
        if api_res['status'] == 'ZERO_RESULTS':
            return []

        v = []
        place = api_res['candidates'][0]
        add_variable_if_exists(v, place, 'name', ('name',))
        add_variable_if_exists(v, place, 'name', ('formatted_address',))
        v.append({
            'name': 'latlon',
            'value': str(place['geometry']['location']['lat']) + ',' + str(place['geometry']['location']['lng']),
        })
        place_id = place['place_id']

        # do a place_details call to get a more concise version of the address
        api_res = self.gmaps.place(
            place_id=place_id,
            fields=['address_component'])
        place = api_res['result']

        for component in place['address_components']:
            if 'political' in component['types']:
                v.append({
                    'name': ' '.join(component for component in component['types'] if component != 'political'),
                    'value': component['long_name'],
                })
        return v

    def distance_matrix(self, source_latitude, source_longitude,
                        destination_latitude, destination_longitude):

        api_res = self.gmaps.distance_matrix(
            origins="{},{}".format(
                source_latitude,
                source_longitude),
            destinations="{},{}".format(
                destination_latitude,
                destination_longitude),
            mode='driving',
            units=self.units)
        if api_res['status'] == 'ZERO_RESULTS':
            return []

        v = []
        logging.debug(
            "DISTANCE MATRIX({}, {}, {}, {}) = {}".format(
                source_latitude,
                source_longitude,
                destination_latitude,
                destination_longitude,
                api_res))

        add_variable_if_exists(
            v,
            api_res,
            'distance',
            ('rows',
             0,
             'elements',
             0,
             'distance',
             'text'))
        add_variable_if_exists(
            v,
            api_res,
            'duration',
            ('rows',
             0,
             'elements',
             0,
             'duration',
             'text'))
        return v

    def places_nearby(self, query, latitude, longitude, num_results=3):
        api_res = self.gmaps.places_nearby(
            name=query, location="{},{}".format(
                latitude, longitude), rank_by='distance')

        v = []
        results = api_res['results'][:num_results]
        logging.debug(
            "PLACES_NEARBY ({}, {}, {}): {}".format(
                query, latitude, longitude, results))
        destinations = []
        for i, place in enumerate(results):
            place_variables = []
            add_variable_if_exists(place_variables, place, 'name', ('name',))
            add_variable_if_exists(
                place_variables, place, 'address', ('formatted_address',))
            add_variable_if_exists(
                place_variables, place, 'rating', ('rating',))
            add_variable_if_exists(
                place_variables, place, 'is_open', ('opening_hours', 'open_now',))
            add_variable_if_exists(
                place_variables, place, 'price_level', ('price_level',))
            add_variable_if_exists(place_variables, place, 'types', ('types',))
            add_variable_if_exists(
                place_variables, place, 'latitude', ('geometry', 'location', 'lat',))
            add_variable_if_exists(
                place_variables, place, 'longitude', ('geometry', 'location', 'lng',))
            destinations.append(
                "{},{}".format(
                    place['geometry']['location']['lat'],
                    place['geometry']['location']['lng']))
            if 'place_id' in place:
                for place_details_variable in self._place_details(
                        place['place_id']):
                    if not any(var['name'] == place_details_variable['name']
                               for var in place_variables):
                        place_variables.append(place_details_variable)
            add_variable_if_exists(
                place_variables, place, 'place_id', ('place_id',))
            v.append({'name': str(i), 'value': place_variables})
        try:
            distances = self.gmaps.distance_matrix(
                origins="{},{}".format(
                    latitude,
                    longitude),
                destinations="|".join(destinations),
                mode='driving',
                units=self.units)
        except googlemaps.exceptions.ApiError as e:
            # If distance matrix fails, try to get as many as possible
            distances = []
            for d in destinations:
                try:
                    distances.append(
                        self.gmaps.distance_matrix(
                            origins="{},{}".format(
                                latitude,
                                longitude),
                            destinations=d,
                            mode='driving',
                            units=self.units))
                except googlemaps.exceptions.ApiError:
                    continue
            return v
        for i, place_variables in enumerate(v):
            add_variable_if_exists(
                place_variables['value'],
                distances,
                'distance',
                ('rows',
                 0,
                 'elements',
                 i,
                 'distance',
                 'text'))
            add_variable_if_exists(
                place_variables['value'],
                distances,
                'duration',
                ('rows',
                 0,
                 'elements',
                 i,
                 'duration',
                 'text'))
        return v

    def start_driving(self, latitude, longitude, place_id):
        '''Dummy call. In theory, this method should actually order the car'''
        return [{'name': 'success', 'value': True}]

    def _place_details(self, place_id):
        v = []
        api_res = self.gmaps.place(
            place_id=place_id,
            fields=[
                'address_component',
                'permanently_closed',
                'vicinity'])
        place = api_res['result']
        logging.debug(
            "PLACE DETAILS (place_id = {}: {}".format(
                place_id, place))
        add_variable_if_exists(v, place, 'address_simple', ('vicinity',))
        add_variable_if_exists(
            v, place, 'permanently_closed', ('permanently_closed',))

        for component in place['address_components']:
            # the API returns a full breakdown of addresses, but only retain
            # the most useful pieces
            if any(key in component['types'] for key in (
                    'street_number', 'route', 'neighborhood', 'locality', 'establishment')):
                v.append({
                    'name': 'street_name' if component['types'] == ['route'] else ' '.join(
                        # filter out some useless keys
                        type_ for type_ in component['types'] if type_ not in ('political', 'point_of_interest')
                    ),
                    'value': component['long_name']
                })
        return v

    def generate_place(self, source_latitude, source_longitude):
        query = random.choice(GoogleMapsProvider.PLACE_QUERIES)
        places = self.places_nearby(
            query,
            source_latitude,
            source_longitude,
            num_results=10)
        place = random.choice(places)
        return place

    def __repr__(self):
        return 'GoogleMapsProvider(keys["google_maps"])'.format(self.api_key)
