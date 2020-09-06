# Config file for the weather domain

import os
import sys
from keys import keys
from domains.domain import Domain

sys.path.append(os.path.join(sys.path[0], '../..'))  # for loading apis

from apis.weather.weather_interface import WeatherInterface
from apis.maps.map_interface import MapInterface

# Initialize interfaces
interfaces = [
    WeatherInterface(keys['darksky'], keys['wit_date']),
    MapInterface('google', keys['google_maps'])
]

# Create a Domain object, which will be used from this file
weather_domain = Domain(
    'weather',
    interfaces,
    'domains/weather/initialization.json',
    'domains/weather/apis.json',
    'domains/weather/agent_templates.txt'
)
