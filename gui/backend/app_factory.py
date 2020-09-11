import functools
import json
import os
import time

from flask import Flask, current_app, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room
from speech import speech2text

from room import Room
from logger.logger import APICallEvent, AgentUtteranceEvent, EndDialogEvent, UserUtteranceEvent
from messages.message_interface import MessageInterface
from utils.filelock import FileLock
from utils.utils import load_templates


class AppFactory():
    def __init__(self, domain, *, agent_class_name=None, agent_model_path=None, user_class_name=None, user_model_path=None, log_path='logs', evaluation_file=None,
                 enable_translate=False, num_rooms=5, starting_evaluation_index=0, user_stories=None, generate_destinations=False, save_logs=True, purge_logs_every_N=0):
        '''
        domain - an instance of domains.Domain
        '''
        self.flask_app = Flask(__name__)
        CORS(self.flask_app)
        # doesn't matter
        self.flask_app.config['SECRET_KEY'] = 'super secret key'
        self.socket = SocketIO(self.flask_app, cors_allowed_origins="*")
        self.domain = domain
        self.save_logs = save_logs

        self._initialize_socket()
        self._initialize_endpoints()

        # create room for each story
        if user_stories is not None:
            # load stories
            with open(user_stories) as f:
                user_stories = json.load(f)
            assert len(user_stories) > 0, "story file is empty."
            print('{} user stories are loaded.'.format(len(user_stories)))
            # get ids of stories that already saved in the log
            saved_stories = set()
            for fn in os.listdir(log_path):
                if not fn.endswith('.json'):
                    continue
                with open(os.path.join(log_path, fn)) as f:
                    log_json = json.load(f)
                    is_sucess = False
                    for e in log_json['events']:
                        if e['event_type'] == 'end_dialog' and e['success'] == True:
                            is_sucess = True
                    if not is_sucess:
                        continue
                    if 'user_story' not in log_json:
                        continue
                    story = log_json['user_story']
                    if not story or 'id' not in story:
                        continue
                    story_id = story['id']
                    saved_stories.add(story_id)
            print(
                '{} stories are saved in log dir.'.format(
                    len(saved_stories)))
            # remove saved stories from the stories to load
            new_stories = []
            for s in user_stories:
                if s['id'] in saved_stories:
                    continue
                new_stories.append(s)
            user_stories = new_stories
            print(
                '{} user stories will be used to create rooms.'.format(
                    len(user_stories)))
            num_rooms = len(user_stories)
        else:
            user_stories = [None] * num_rooms

        # create rooms ids
        if None not in user_stories:  # use story id as room id if possible
            room_ids = [story['id'] for story in user_stories]
        else:
            room_ids = [str(i) for i in range(num_rooms)]

        # create rooms
        self.rooms = {}
        agent_shared_state = {}
        user_shared_state = {}
        for i, room_id in enumerate(room_ids):
            handle_end_dialog = functools.partial(self.end_dialog_confirm, room_id=room_id)
            self.rooms[room_id] = Room(
                room_id, self.socket, domain,
                agent_shared_state, agent_class_name, agent_model_path,
                user_shared_state, user_class_name, user_model_path,
                handle_end_dialog, log_path, evaluation_file, enable_translate,
                starting_evaluation_index=starting_evaluation_index,
                user_story=user_stories[i],
                generate_destinations=generate_destinations,
                purge_logs_every_N=purge_logs_every_N
            )

            # Only set up room 0 in evaluation mode
            evaluation_file = None

        for interface in domain.interfaces:
            interface.create_endpoints(self.flask_app, self.rooms)

    def start(self, port, debug=False):
        self.socket.run(self.flask_app, host="0.0.0.0", port=port, debug=debug)

    def _initialize_socket(self):
        '''Initialize socket endpoints'''

        @self.socket.on('join')
        def handle_join(msg):
            room_id = msg['roomId']
            if not room_id in self.rooms:
                self.socket.emit('join_error')
                return
            room = self.rooms[room_id]
            join_room(room_id)
            room.message_interface.handle_connection(
                msg['sender'],
                room.manager.request_variables,
                room.manager.user_destination)

        @self.socket.on('/message')
        def handle_message(msg, methods=['GET', 'POST']):
            room_id = msg['roomId']
            room = self.rooms[room_id]
            room.message_interface.handle_message(msg)

        @self.socket.on('/restart_dialog')
        def handle_restart_dialog(msg):
            room_id = msg['roomId']
            room = self.rooms[room_id]
            self.socket.emit("/restart_dialog", room=msg['roomId'])
            room.complete_dialog(completed=False, correct=False)

        @self.socket.on('/end_dialog_confirm')
        def handle_end_dialog_confirm(msg):
            self.end_dialog_confirm(msg['correct'], msg['roomId'])

    def end_dialog_confirm(self, correct, room_id):
        room = self.rooms[room_id]
        filename = room.logger.save_logs(
            correct,
            room.agent.name,
            room.user_story) if self.save_logs else 'dummy'
        self.socket.emit('/end_dialog_confirm',
                         {'correct': correct,
                          'filename': filename},
                         room=room_id)
        room.correct_dialogs += correct
        room.complete_dialog(completed=True, correct=correct)

    def create_test_clients(self):
        '''Return a flask and socket client for testing'''
        self.flask_app.testing = True
        flask_client = self.flask_app.test_client()
        socket_client = self.socket_client = self.socket.test_client(
            self.flask_app)

        return flask_client, socket_client

    def _initialize_endpoints(self):
        '''Create endpoints'''
        @self.flask_app.route('/rooms', methods=['GET'])
        def rooms():
            return jsonify(
                [{'id': k, 'isEvaluation': self.rooms[k].evaluation_table is not None} for k in self.rooms])

        @self.flask_app.route('/templates/<sender>', methods=['GET', 'POST'])
        def templates(sender):
            template_file = getattr(self.domain, '{}_templates'.format(sender))

            if request.method == 'GET':
                templates_list = load_templates(template_file)
                return jsonify(templates_list)
            elif request.method == 'POST':
                request_body = request.json
                with FileLock(template_file):
                    with open(template_file, 'r+') as f:
                        new_template_lines = []
                        template_written = False
                        template_lines = f.readlines()
                        for line in template_lines:
                            line = line.strip('\n')
                            new_template_lines.append(line)
                            if line.startswith('---'):
                                template_group = line.rstrip(
                                    ' ---').lstrip('--- ')
                                if request_body['group'] == template_group:
                                    template_written = True
                                    new_template_lines.append(
                                        request_body['template'])
                        if not template_written:
                            new_template_lines.append(request_body['template'])
                    with open(template_file, 'w') as f:
                        f.write('\n'.join(new_template_lines))
                    templates_list = load_templates(template_file)
                return jsonify(templates_list)

        @self.flask_app.route('/apis')
        def apis():
            with current_app.open_resource(self.domain.apis_file, 'r') as f:
                api_list = json.load(f)
            return jsonify(api_list)

        @self.flask_app.route('/<room_id>/user/options',
                              methods=['GET', 'POST'])
        def user_options(room_id):
            if not room_id in self.rooms:
                return
            room = self.rooms[room_id]
            if request.method == 'POST':
                room.message_interface.user.language = request.json.get(
                    'inputLanguage')
                room.message_interface.input_type = request.json.get(
                    'inputType')
                room.manager.set_initial_variables(
                    request.json.get('initialVariables'))
                response = {
                    'status': 'ok'
                }
                return jsonify(response)
            elif request.method == 'GET':
                options = {
                    'inputLanguage': room.message_interface.user.language,
                    'inputType': room.message_interface.input_type,
                    'initialVariables': room.manager.get_initial_variables(),
                    'evaluationProgress': {},
                    'userStory': {}
                }
                if room.evaluation_table is not None:
                    options['evaluationProgress']['currentIndex'] = room.evaluation_index
                    options['evaluationProgress']['total'] = len(
                        room.evaluation_table),
                    options['evaluationProgress']['endHint'] = room.manager.end_hint
                if room.user_story is not None:
                    options['userStory']['story'] = room.user_story['story']
                    options['userStory']['destinationName'] = room.user_story['destination_name']
                    options['userStory']['destinationAddr'] = room.user_story['destination_addr']
                    options['userStory']['sourceAddr'] = room.user_story['source_addr']
                return jsonify(options)

        @self.flask_app.route('/<room_id>/give_up', methods=['POST'])
        def handle_give_up(room_id):
            room = self.rooms[room_id]
            room.manager.end_dialog(False, None, 'give_up', {})
            return jsonify([])

        @self.flask_app.route('/<room_id>/agent_name', methods=['GET', 'POST'])
        def agent_name(room_id):
            room = self.rooms[room_id]
            if request.method == 'GET':
                return jsonify({'agent_name': room.agent.name})
            else:
                room.agent_name = request.json.get('agent_name')
            return jsonify({'status': 'ok'})

        @self.flask_app.route('/<room_id>/state', methods=['GET', 'POST'])
        def state(room_id):
            room = self.rooms[room_id]
            return jsonify(room.state())

        @self.flask_app.route('/<room_id>/speech2text', methods=['POST'])
        def speech_to_text(room_id):
            request_body = request.files

            res = request_body['audio'].read()
            s_time = time.time()
            transcribe_result = speech2text.backend_process(
                res, MessageInterface.LANGUAGE_CODES[self.message_interface.user.language])
            e_time = time.time()
            print("speech2text api cost time:{}".format(e_time - s_time))

            msg_template = {
                'sender': 'user',
                'body': transcribe_result,
                'inputType': 'speech'}
            self.message_interface.handle_message(msg_template)

            return jsonify("nothing")

        @self.flask_app.route('/<room_id>/execute_alternate_action',
                              methods=['POST'])
        def execute_alternate_action(room_id):
            message = request.json
            room = self.rooms[room_id]

            message_id = str(message['id'])
            breakdown_event_index, total_num_breakdown_events = message[
                "dropdown_indices_and_lengths"][0]
            alternate_event_index_to_swap_in, _ = message["dropdown_indices_and_lengths"][1]

            message_to_modify = None
            message_to_modify_index = None
            for index, message in enumerate(
                    reversed(room.message_interface.messages)):
                if message['sender'] in ['agent', 'user'] and message.get(
                        "id") == message_id:
                    message_to_modify = message
                    message_to_modify_index = (index + 1) * -1
                    break
            assert message_to_modify is not None, "Couldn't find message_id %s" % message_id
            event_to_swap_out = message_to_modify["breakdown_events"][breakdown_event_index]
            event_to_swap_in = event_to_swap_out["alternate_events"]["events"][alternate_event_index_to_swap_in]

            log_event_to_swap_out_index = None
            for index, e in enumerate(
                    reversed(room.message_interface.logger.all_events)):
                if isinstance(e, AgentUtteranceEvent) or isinstance(
                        e, UserUtteranceEvent):
                    if e.message.get("id", None) == message_id:
                        utterance_log_index = (index + 1) * -1
                        log_event_to_swap_out_index = utterance_log_index - \
                            (total_num_breakdown_events - breakdown_event_index - 1)
                        break
            assert log_event_to_swap_out_index is not None, "Couldn't find message_id %s in log events" % message_id
            log_event_to_swap_out = room.message_interface.logger.all_events[
                log_event_to_swap_out_index]

            # Back-up and clear state
            cleared_events = room.message_interface.logger.all_events[log_event_to_swap_out_index:]
            room.message_interface.logger.all_events = room.message_interface.logger.all_events[
                :log_event_to_swap_out_index]
            room.message_interface.messages = room.message_interface.messages[
                :message_to_modify_index]
            room.message_interface.socket.emit(
                '/history/messages', room.message_interface.messages, room=room_id)

            num_request_variables_to_clear = len(
                [e for e in cleared_events if isinstance(e, APICallEvent)])
            if num_request_variables_to_clear:
                room.manager.request_number -= num_request_variables_to_clear
                room.manager.request_variables = room.manager.request_variables[:(
                    -1 * num_request_variables_to_clear)]
                room.message_interface.socket.emit('/history/request_variables/agent',
                                                   room.manager.request_variables,
                                                   room=room_id)

            num_user_utterance_variables_to_clear = len(
                [e for e in cleared_events if isinstance(e, UserUtteranceEvent)])
            if num_user_utterance_variables_to_clear:
                room.message_interface.user_utterance_variables = room.message_interface.user_utterance_variables[:(
                    -1 * num_user_utterance_variables_to_clear)]
                room.message_interface.user_utterance_variables_without_full_names = room.message_interface.user_utterance_variables_without_full_names[:(
                    -1 * num_user_utterance_variables_to_clear)]
                room.message_interface.user_utterance_number -= num_user_utterance_variables_to_clear
                room.message_interface.socket.emit(
                    '/history/user_utterance_variables',
                    room.message_interface.user_utterance_variables_without_full_names,
                    room=room_id)

            if room.message_interface.agent is not None:
                room.message_interface.queued_events = set([])
                initial_alternate_events = log_event_to_swap_out.message["alternate_events"] if isinstance(
                    log_event_to_swap_out, AgentUtteranceEvent) or isinstance(
                    log_event_to_swap_out, UserUtteranceEvent) else log_event_to_swap_out.alternate_events
                alternate_event_index_to_swap_out = initial_alternate_events["active_index"]
                if alternate_event_index_to_swap_out not in initial_alternate_events[
                        "failed_indexes"]:
                    initial_alternate_events["failed_indexes"].append(
                        alternate_event_index_to_swap_out)
                initial_alternate_events["active_index"] = alternate_event_index_to_swap_in
                if alternate_event_index_to_swap_in in initial_alternate_events["failed_indexes"]:
                    initial_alternate_events["failed_indexes"].remove(
                        alternate_event_index_to_swap_in)
                room.message_interface.send_agent_message(None, room.manager.request_variables,
                                                          initial_alternate_events=initial_alternate_events)
            return jsonify({'status': 'ok'})
