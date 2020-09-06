import argparse
import logging
import csv
import json

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def story_hit2json(args):
    out = []
    with open(args.story_hit_csv) as f, open(args.out_json, 'w') as f_out:
        stories = csv.DictReader(f, delimiter=',')
        for row in stories:
            story_id = row['AssignmentId']
            sentences = [row['Answer.sentence_{}'.format(
                sent_idx)].strip() for sent_idx in range(1, 7)]
            sentences = [s for s in sentences if s]
            starting_addr = row['Answer.starting_address']
            dest_name = row['Answer.destination_name'] if 'Answer.destination_name' in row else ''
            dest_addr = row['Answer.destination_address']
            story = {
                "id": story_id,
                "source_addr": starting_addr,
                "destination_name": dest_name,
                "destination_addr": dest_addr,
                "story": sentences
            }
            out.append(story)

        json.dump(out, f_out, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('story_hit_csv')
    parser.add_argument('out_json')
    args, _ = parser.parse_known_args()

    story_hit2json(args)


if __name__ == "__main__":
    main()
