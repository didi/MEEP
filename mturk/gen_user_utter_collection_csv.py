import argparse
import logging
import json
import os

logging.basicConfig(format='%(asctime)s: %(levelname)s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()


def gen_user_utter_collection_csv(args):
    stories = json.load(open(args.story_json))

    old_story_ids = set()
    for fn in os.listdir(args.old_log_dir):
        if not fn.endswith('.json'):
            continue
        log = json.load(open(os.path.join(args.old_log_dir, fn)))
        try:
            story_id = log['user_story']['id']
            old_story_ids.add(story_id)
        except BaseException:
            pass

    current_stories_ids = []
    for s in stories:
        if s['id'] in old_story_ids:
            pass
        current_stories_ids.append(s['id'])

    new_logged_story_ids = set()
    for fn in os.listdir(args.new_log_dir):
        if not fn.endswith('.json'):
            continue
        log = json.load(open(os.path.join(args.new_log_dir, fn)))
        try:
            story_id = log['user_story']['id']
            new_logged_story_ids.add(story_id)
        except BaseException:
            pass

    for i, s_id in enumerate(current_stories_ids):
        if s_id in new_logged_story_ids:
            print(i)

    # with open(args.out_csv, 'w') as f_out:
    #   f_out.write('user_interface_url\n')
    #   for i in range(args.num_of_rooms):
    #     f_out.write('{}/{}/user\n'.format(args.url, i))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    parser.add_argument('story_json', type=int)
    parser.add_argument('old_log_dir')
    parser.add_argument('new_log_dir')
    parser.add_argument('out_csv')
    args, _ = parser.parse_known_args()

    gen_user_utter_collection_csv(args)


if __name__ == "__main__":
    main()
