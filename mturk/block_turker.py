import argparse
import logging
import csv
import json
import collections

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def block_turker(args):
    with open(args.story_csv) as f_csv, open(args.curated_story_json) as f_json:
        stories = csv.DictReader(f_csv, delimiter=',')
        story_ids = []
        for row in stories:
            story_ids.append((row['HITId'], row['WorkerId']))

        curated_story_ids = []
        for story in json.load(f_json):
            curated_story_ids.append(story['id'])

        logger.info('turker IDs to block:')
        work_status = collections.defaultdict(
            lambda: collections.defaultdict(int))
        for story_id, worker_id in story_ids:
            if story_id in curated_story_ids:
                work_status[worker_id]['accept'] += 1
                continue
            else:
                work_status[worker_id]['reject'] += 1
        for worker_id, status in work_status.items():
            if 'reject' in status:
                logger.info(
                    '{} - accept: {} - reject: {}'.format(
                        worker_id, status['accept'], status['reject']
                    )
                )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('story_csv')
    parser.add_argument('curated_story_json')
    args, _ = parser.parse_known_args()

    block_turker(args)


if __name__ == "__main__":
    main()
