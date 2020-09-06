import copy
import functools
import json
import os
import sys
import time

from logger.logger import Logger
from messages.message_interface import MessageInterface

sys.path.extend([
    os.path.join(sys.path[0], '../..')  # for loading apis and agents
])
from agents.agent import create_agent
from apis import VariableManager, MapInterface
from users.user import create_user


class Room():
    '''
    Configuration for a single server. This handles logging and state.
    TODO: this should also handle isolating messages
    '''

    def __init__(self, room_id, socket, domain, agent_shared_state, agent_class_name=None, agent_model_path=None, user_shared_state=None, user_class_name=None, user_model_path=None, handle_end_dialog=None, log_path='logs', evaluation_file=None, enable_translate=False, starting_evaluation_index=0, user_story=None, generate_destinations=False, purge_logs_every_N=0):
        self.emit_fn = functools.partial(socket.emit, room=room_id)
        self.socket = socket

        self.logger = Logger(
            domain.interfaces,
            room_id=room_id,
            log_path=log_path,
            purge_every_N=purge_logs_every_N)

        get_user_destination = None
        if generate_destinations:
            for interface in domain.interfaces:
                if isinstance(interface, MapInterface):
                    def get_user_destination(lat, lng): return interface.generate_place([
                        {'param': 'src latitude', 'value': lat},
                        {'param': 'src longitude', 'value': lng},
                    ])

        self.user = create_user(user_class_name, user_shared_state, user_model_path, domain=domain)
        self.user_name = user_class_name
        self.user.room = self

        with open(domain.initialization) as fh:
            self.initialization = json.load(fh)

        self.manager = VariableManager(
            self.emit_fn,
            self.logger,
            self.initialization['initial_variables'],
            get_user_destination,
            handle_end_dialog,
            self.user)

        self.interfaces = []
        for interface in domain.interfaces:
            new_interface = copy.copy(interface)
            new_interface.manager = self.manager
            self.interfaces.append(new_interface)
        self.agent = create_agent(agent_class_name, agent_shared_state,
                                  agent_model_path, self.interfaces, domain=domain)
        self.agent.room = self

        self.enable_translate = enable_translate

        self.message_interface = MessageInterface(
            self.agent, self.user, socket, self.emit_fn, self.logger,
            initial_message=self.initialization['initial_message'],
            enable_translate=enable_translate
        )

        evaluation_file = evaluation_file if evaluation_file else None
        self.evaluation_table = None if evaluation_file is None else []
        if evaluation_file is not None:
            with open(evaluation_file) as f:
                for line in f:
                    line = line.strip().split('\t')
                    self.evaluation_table.append({
                        'starting_address': line[0],
                        'first_utterance': line[1],
                        'destination_description': line[2]
                    })
                    if len(line) >= 4:
                        log_file_basename = os.path.basename(line[3])
                        if log_file_basename.endswith(".json"):
                            log_file_basename = log_file_basename[:-1 * len(
                                ".json")]
                        self.evaluation_table[-1]["log_file"] = log_file_basename

            self.evaluation_index = starting_evaluation_index

        # add user story
        self.user_story = user_story

        self.correct_dialogs = 0
        self.initialize()

    def set_agent(self, agent, agent_name=None):
        '''Change the agent and wipe the message history'''

        self.agent = agent
        if agent_name is not None:
            self.agent.name = agent_name
        self.message_interface = MessageInterface(
            self.agent,
            self.user,
            self.socket,
            self.emit_fn,
            self.logger,
            initial_message=self.initialization['initial_message'],
            enable_translate=self.enable_translate)
        self.logger.agent_name = agent.name
        self.complete_dialog(completed=False)

    def setup_evaluation_if_needed(self):
        if self.evaluation_table is None:
            return
        current_evaluation = self.evaluation_table[self.evaluation_index]
        # Set source
        for interface in self.interfaces:
            if isinstance(interface, MapInterface):
                current_source = self.manager.get_initial_variables()
                new_source = interface.map_provider.find_place(
                    current_evaluation['starting_address'],
                    current_source['latitude'],
                    current_source['longitude'])
                new_source = [
                    v for v in new_source if v['name'] in (
                        'address', 'latitude', 'longitude')]
                if len(new_source) == 3:
                    self.manager.set_source({
                        'address': new_source[0]['value'],
                        'latitude': new_source[1]['value'],
                        'longitude': new_source[2]['value']
                    })
                break
        self.manager.set_end_hint(
            current_evaluation['destination_description'])
        if "log_file" in current_evaluation:
            self.logger.filename = os.path.join(
                os.path.abspath(
                    self.logger.log_path),
                current_evaluation['log_file'])
        # Send initial message
        self.message_interface.handle_message({
            'sender': 'user',
            'body': current_evaluation['first_utterance'],
            'inputType': 'text'
        })
        self.emit_fn("/evaluation_progress",
                     {'currentIndex': self.evaluation_index,
                      'total': len(self.evaluation_table),
                         'destinationHint': current_evaluation['destination_description']})

    def finish_evaluation_dialog_if_needed(self):
        if self.evaluation_table is None:
            return
        # Setup next evaluation, check if finished
        self.evaluation_index += 1
        if self.evaluation_index == len(self.evaluation_table):
            with open(os.path.join(self.logger.log_path, "evaluation_result_{}.json".format(int(time.time()))), 'w') as f:
                json.dump({
                    'success_rate': self.correct_dialogs / max(1, len(self.evaluation_table)),
                    'correct': self.correct_dialogs,
                    'total': len(self.evaluation_table),
                    'agent': self.agent.name
                }, f, indent=4)
            self.emit_fn("/finished_evaluation",
                         {'success_rate': self.correct_dialogs / max(1,
                                                                     len(self.evaluation_table))})
            # Restart evaluation
            self.correct_dialogs = 0
            self.evaluation_index = 0

    def setup_user_story_if_needed(self):
        if self.user_story is None:
            return

        # set source
        for interface in self.interfaces:
            if isinstance(interface, MapInterface):
                current_source = self.manager.get_initial_variables()
                new_source = interface.map_provider.find_place(
                    self.user_story['source_addr'], current_source['latitude'],
                    current_source['longitude'])
                new_source = [v for v in new_source if
                              v['name'] in ('address', 'latitude', 'longitude')]
                if len(new_source) == 3:
                    self.manager.set_initial_variables({
                        'address': new_source[0]['value'],
                        'latitude': new_source[1]['value'],
                        'longitude': new_source[2]['value']
                    })
                break

        self.emit_fn(
            "/user_story",
            {'story': self.user_story['story'],
             'destinationName': self.user_story['destination_name'],
             'destinationAddr': self.user_story['destination_addr'],
             'sourceAddr': self.user_story['source_addr']
             },
        )

    def initialize(self):
        self.logger.all_events[:] = []
        self.manager.clear_variables()
        self.agent.reset(self.manager.get_initial_variables())
        self.user.reset()
        self.finish_evaluation_dialog_if_needed()
        self.setup_evaluation_if_needed()
        self.setup_user_story_if_needed()
        self.message_interface.initialize()

    def complete_dialog(self, completed=False, correct=False):
        self.agent.on_dialog_finished(completed, correct)
        self.user.on_dialog_finished(completed, correct)
        self.initialize()

    def state(self):
        return {
            'dialog_history': self.message_interface.messages if hasattr(self, 'message_interface') else [],
            'destination_variables': self.manager.user_destination,
            'initial_variables': self.manager.initial_variables,
            'request_variables': self.manager.request_variables,
            'agent_utterance_variables': self.message_interface.agent_utterance_variables if hasattr(self, 'message_interface') else [],
            'user_utterance_variables': self.message_interface.user_utterance_variables if hasattr(self, 'message_interface') else []
        }
