# Reads keys from a file (api_keys.json). Don't commit that file!

import json
import os
import shutil

key_path = os.path.join(os.path.dirname(__file__), 'api_keys.json')
# If using a shared machine, copy from a centralized location
if not os.path.isfile(key_path) and os.path.isfile(
        '/home/shared/keys/api_keys.json'):
    print('Copying keys from shared directory')
    shutil.copyfile('/home/shared/keys/api_keys.json', key_path)

keys = {}
if os.path.isfile(key_path):
    with open(key_path) as fh:
        keys = json.load(fh)
