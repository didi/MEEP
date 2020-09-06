from apis.base import BaseInterface
from apis.utils import load_parameter, route, completes_dialog, add_adjacent_variable
from apis.maps.google_maps_apis import GoogleMapsProvider

from apis.maps.microworld_provider import MicroworldMapProvider

providers = {
    'google': GoogleMapsProvider,
    'microworld': MicroworldMapProvider,
}

class MapInterface(BaseInterface):
    '''Component to abstract out which map provider is used'''

    def __init__(self, map_provider, *args, **kwargs):
        super().__init__()
        self.map_provider = providers[map_provider](*args, **kwargs)
        self.provider = self.map_provider  # TODO: change name map_provider -> provider

    @route('/maps/find_place', methods=['POST'])
    def find_place(self, request_params, alternate_events=None):
        query = load_parameter(request_params, "query")
        latitude = load_parameter(request_params, "src latitude")
        longitude = load_parameter(request_params, "src longitude")
        response = self.api_call(self.map_provider.find_place, request_params, query, latitude, longitude,
                                 alternate_events=alternate_events)
        return response

    @route('/maps/find_latlon', methods=['POST'])
    def find_latlon(self, request_params, alternate_events=None):
        '''find_place, but only returns lat/long'''
        query = load_parameter(request_params, "query")
        latlon = load_parameter(request_params, "src lat/long")

        # find_latlon is currently only supported with google maps
        response = self.api_call(self.map_provider.find_latlon, request_params, query, latlon,
                                 alternate_events=alternate_events)

        return response

    @route('/maps/distance_matrix', methods=['POST'])
    def distance_matrix(self, request_params, alternate_events=None):
        source_latitude = load_parameter(request_params, "src latitude")
        source_longitude = load_parameter(request_params, "src longitude")
        dest_latitude = load_parameter(request_params, "dest latitude")
        dest_longitude = load_parameter(request_params, "dest longitude")
        return self.api_call(self.map_provider.distance_matrix, request_params, source_latitude,
                             source_longitude, dest_latitude, dest_longitude, alternate_events=alternate_events)

    @route('/maps/places_nearby', methods=['POST'])
    def places_nearby(self, request_params, alternate_events=None):
        query = load_parameter(request_params, "query")
        latitude = load_parameter(request_params, "src latitude")
        longitude = load_parameter(request_params, "src longitude")
        return self.api_call(self.map_provider.places_nearby, request_params, query, latitude, longitude,
                             alternate_events=alternate_events)

    @route('/maps/generate_place', methods=['GET'])
    def generate_place(self, request_params):
        latitude = load_parameter(request_params, "src latitude")
        longitude = load_parameter(request_params, "src longitude")
        return self.map_provider.generate_place(latitude, longitude)

    @route('/maps/start_driving', methods=['POST'])
    @add_adjacent_variable(param_name="dest id",
                           replacement=("latitude", "place_id"))
    @completes_dialog(success=True, confirmation_type='map')
    def start_driving(self, request_params, alternate_events=None):
        latitude = load_parameter(request_params, "dest latitude")
        longitude = load_parameter(request_params, "dest longitude")
        place_id = load_parameter(request_params, "dest id")
        return self.api_call(self.map_provider.start_driving, request_params, latitude, longitude, place_id,
                             alternate_events=alternate_events)

    @route('/maps/start_driving_no_map', methods=['POST'])
    @completes_dialog(success=True, confirmation_type='confirm_information')
    def start_driving_no_map(self, request_params, alternate_events=None):
        '''Start driving with a text confirmation instead of a map'''
        latitude = load_parameter(request_params, "dest latitude")
        longitude = load_parameter(request_params, "dest longitude")

        # we can't reliably split the variable name into entity and variable type because
        # variable names can include v2_0_rating and v1_place_id
        destination_name_variable = request_params[0]['variable_name'].replace(
            'latitude', 'name')
        destination_address_variable = request_params[0]['variable_name'].replace(
            'latitude', 'address')
        destination_name = self.manager.lookup_variable_by_name(
            destination_name_variable)
        destination_address = self.manager.lookup_variable_by_name(
            destination_address_variable)

        request_params.append({
            'name': 'confirmationString',
            'variable_name': 'confirmationString',
            'value': 'The agent selected your destination as {} at {} ({}, {}). Is this correct?'
            .format(destination_name, destination_address, latitude, longitude)
        })
        return self.api_call(self.map_provider.start_driving_no_map, request_params,
                             latitude, longitude, alternate_events=alternate_events)
