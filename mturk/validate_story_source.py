import argparse
import logging
import json
from gui.backend.keys import keys
from apis import MapInterface

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()

current_source = {'latitude': 33.9816425,
                  'longitude': -118.4409761,
                  'address': '4640 Admiralty Way, Marina del Rey'}


def validate_story_source(args):
    interface = MapInterface('google', keys['google_maps'])

    with open(args.story_json) as f:
        story_json = json.load(f)
        for story in story_json[:10]:
            source_addr = story['source_addr']
            new_source = interface.map_provider.find_place(
                source_addr, current_source['latitude'], current_source['longitude'])
            print('new source len: {}'.format(len(new_source)))
            new_source = [
                v for v in new_source if v['name'] in (
                    'address', 'latitude', 'longitude')]
            print('new_source', new_source)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('story_json')
    args, _ = parser.parse_known_args()

    validate_story_source(args)


if __name__ == "__main__":
    main()
