import argparse
from datetime import datetime
import logging
import os
import sys

from app_factory import AppFactory
from keys import keys
from domains.domain import load_domain

def load_args():
    parser = argparse.ArgumentParser(
        description='Server for dialog collection')
    parser.add_argument('--agent_class_name',
                        help='Python path of automatic-agent class name. ' +
                        'Do not specify this arg if a human is acting as agent', nargs='?', default=None)
    parser.add_argument('--agent_model_path',
                        help='Optional file/dir to agent model and config, only used when --agent_class_name is specified',
                        default=None,
                        )
    parser.add_argument('--user_class_name',
                        help='Python path of automatic-user class name.',
                        default=None
                        )
    parser.add_argument('--user_model_path',
                        help='Optional file/dir to user model and config, ' +
                             'only used when --user_class_name is specified',
                        default=None,
                        )
    parser.add_argument(
        '--port',
        help='Port to run backend on.',
        nargs='?',
        default=5000)
    parser.add_argument(
        '--domain',
        default='destination',
        help='name of external API interfaces to add (default options are destination, weather, microworld OR a full python path, e.g. microworld.config.microworld_domain). See apis folder for a description of the domains')
    parser.add_argument(
        '--log_dir',
        help='Where completed dialogs will be logged.',
        default=None)
    parser.add_argument(
        '--evaluation_file',
        default=None,
        help='Input file containing evaluation prompts, if running in evaluation mode')
    parser.add_argument('--evaluation_start_index', default=0, type=int,
                        help='If running in evaluation mode, the prompt index to start evaluation at. Index begins at 0.')
    parser.add_argument('--num_rooms', default=5, type=int,
                        help='Number of parallel chat rooms to support, that each can carry a separate conversation.')
    parser.add_argument('--user_stories', default=None,
                        help='JSON file that contains a list of stories to help user interact with the agent.')
    parser.add_argument('--generate_destinations', action='store_true', default=False,
                        help='Whether or not to generate destinations')
    parser.add_argument('--dont_save', action='store_true', default=False,
                        help='Whether to run without saving logs (for RL experiments)')
    parser.add_argument('--purge_logs_every_N', default=0, type=int,
                        help='Purge the log directory every N logs, only safe with 1 room.')
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Whether to run the flask server in debug mode')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    print('Starting server at ', datetime.today().isoformat())

    # Parse args
    args = load_args()
    assert args.purge_logs_every_N <= 0 or args.num_rooms == 1

    if 'google_speech' in keys:
        # TODO(SF): Disable front-end UI components that use this api key,
        # (TTS, translation)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keys['google_speech']

    # Initialize domain
    domain = load_domain(args.domain)

    # Set up logging
    if args.log_dir is None:
        args.log_dir = 'logs/{}'.format(args.domain)
    os.makedirs(args.log_dir, exist_ok=True)

    # Initialize app
    app = AppFactory(
        domain,
        agent_class_name=args.agent_class_name,
        agent_model_path=args.agent_model_path,
        user_class_name=args.user_class_name,
        user_model_path=args.user_model_path,
        log_path=args.log_dir, evaluation_file=args.evaluation_file,
        num_rooms=args.num_rooms,
        starting_evaluation_index=args.evaluation_start_index,
        user_stories=args.user_stories,
        generate_destinations=args.generate_destinations,
        save_logs=not args.dont_save,
        purge_logs_every_N=args.purge_logs_every_N
    )

    # Run app
    logging.basicConfig(filename='server_log.txt', level=logging.DEBUG)
    app.start(args.port, debug=args.debug)
