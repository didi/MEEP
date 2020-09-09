# Config file for the microworld domain

import sys
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
sys.path.append(str(REPO_ROOT))  # For loading apis
sys.path.append(str(REPO_ROOT / "gui" / "backend"))  # For loading domains

from domains.domain import Domain
from apis.maps.map_interface import MapInterface

# Initialize interfaces
interfaces = [
    MapInterface('microworld', map_path='microworld_map.txt')
]

# Create a Domain object, which will be used from this file
DOMAIN_DIR = REPO_ROOT / "gui/backend/domains/microworld"
microworld_domai1 = Domain(
    'microworld1',
    interfaces,
    initialization_file=DOMAIN_DIR / 'initialization1.json',
    apis_file=DOMAIN_DIR / 'apis.json',
    agent_templates=DOMAIN_DIR / 'agent_templates.txt',
    user_templates=DOMAIN_DIR / 'user_templates.txt',
)

# Microworld v2
microworld_domain2 = Domain(
    'microworld2',
    [MapInterface('microworld', map_path='microworld_map2.txt')],
    initialization_file=DOMAIN_DIR / 'initialization2.json',
    apis_file=DOMAIN_DIR / 'apis.json',
    agent_templates=DOMAIN_DIR / 'agent_templates.txt',
    user_templates=DOMAIN_DIR / 'user_templates.txt',
)
