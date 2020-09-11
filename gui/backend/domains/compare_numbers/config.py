# Config file for the compare_numbers domain

import os
import sys
import pathlib
from keys import keys
from domains.domain import Domain

REPO_ROOT = str(pathlib.Path(__file__).resolve().parents[4])
sys.path.append(REPO_ROOT)  # For loading apis

from apis.compare_numbers.compare_numbers_interface import CompareNumbersInterface

# Initialize interfaces
interfaces = [
    CompareNumbersInterface(),
]

# Create a Domain object, which will be used from this file
domain_dir = pathlib.Path(__file__).resolve().parents[0]

compare_numbers_domain = Domain(
    'compare_numbers',
    interfaces,
    initialization_file=domain_dir / 'initialization.json',
    apis_file=domain_dir / 'apis.json',
    agent_templates=domain_dir / 'agent_templates.txt',
)
