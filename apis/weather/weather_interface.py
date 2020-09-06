from apis.weather.weather_provider import WeatherProvider
from apis.base import BaseInterface
from apis.utils import load_parameter, route, completes_dialog


class WeatherInterface(BaseInterface):
    '''Query the weather'''

    def __init__(self, darksky_key, wit_key):
        super().__init__()
        self.provider = WeatherProvider(darksky_key, wit_key)

    @route('/weather/current', methods=['POST'])
    def current(self, request_params):
        '''Return the current weather'''
        lat_long = load_parameter(request_params, "lat/long")
        lat, lon = lat_long.split(',')
        response = self.api_call(
            self.provider.current_weather,
            request_params,
            lat,
            lon)
        return response

    @route('/weather/at_time', methods=['POST'])
    def at_time(self, request_params):
        '''Return the current weather at the specified time'''

        lat_long = load_parameter(request_params, "lat/long")
        lat, lon = lat_long.split(',')
        time_query = load_parameter(request_params, "time query")
        response = self.api_call(
            self.provider.weather_at_time,
            request_params,
            lat,
            lon,
            time_query)
        return response

    @route('/rate_satisfaction', methods=['POST'])
    @completes_dialog(success=True, confirmation_type='rate_satisfaction')
    def rate_satisfaction(self, request_params):
        return self.api_call(self.provider.rate_satisfaction, request_params)
