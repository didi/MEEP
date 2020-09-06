from apis.manager import VariableManager

# Export all interfaces
from apis.maps.map_interface import MapInterface
from apis.weather.weather_interface import WeatherInterface
from apis.compare_numbers.compare_numbers_interface import CompareNumbersInterface

# Export all providers for logs
from apis.maps.google_maps_apis import GoogleMapsProvider
from apis.maps.microworld_provider import MicroworldMapProvider
from apis.weather.weather_provider import WeatherProvider
from apis.compare_numbers.compare_numbers_provider import CompareNumbersProvider
