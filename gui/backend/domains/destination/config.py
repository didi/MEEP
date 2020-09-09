# Config file for the destination domain

import os
import sys
from keys import keys
from domains.domain import Domain

sys.path.append(os.path.join(sys.path[0], '../..'))  # for loading apis

from apis.maps.map_interface import MapInterface

# Initialize interfaces
interfaces = [
    MapInterface('google', keys['google_maps'])
]

# Create a Domain object, which will be used from this file
destination_domain = Domain(
    'destination',
    interfaces,
    initialization_file='domains/destination/initialization.json',
    apis_file='domains/destination/apis.json',
    agent_templates='domains/destination/agent_templates.txt',
    user_templates='domains/destination/user_templates.txt',
)
