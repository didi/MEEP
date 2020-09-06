import copy
import nltk
import os
import sys
from uuid import uuid4

from google.cloud import translate_v2 as translate

sys.path.extend([
    os.path.join(sys.path[0], '../..')  # for loading users and agents
])
from agents.human_agent import HumanAgent
from speech import text2speech
from logger.logger import APICallEvent, AgentUtteranceEvent, EndDialogEvent, UserUtteranceEvent
from users.human_user import HumanUser
from utils.utils import add_full_names, freeze


class MessageInterface():
    '''Class that maintains the message history'''

    DEFAULT_INPUT_TYPE = "text"
    DEFAULT_AGENT_GREETING = {
        'body': "Hello! Where would you like to go today?",
        'template': "Hello! Where would you like to go today?",
        'variables': [],
        'sender': 'agent'
    }
    LANGUAGE_CODES = {
        "en": "en-US",
        "es": "es-MX",
        "zh": "zh-CN",
        "ru": "ru-RU",
        "fr": "fr-FR"
    }

    def __init__(self, agent, user, socket, emit_fn, logger,
                 initial_message=None, enable_translate=True):
        self.agent = agent
        self.user = user
        self.socket = socket
        self.emit_fn = emit_fn
        self.logger = logger
        self.translate_client = translate.Client(
        ) if self.agent.language is not '*' and enable_translate else None
        self.initial_message = initial_message if initial_message is not None else MessageInterface.DEFAULT_AGENT_GREETING
        self.input_type = MessageInterface.DEFAULT_INPUT_TYPE

        self.queued_events = set()  # cancellable delayed messages

        try:
            nltk.word_tokenize('test')
        except LookupError:
            print("Could not find NLTK tokenizer, downloading...")
            nltk.download('punkt')
            print("Downloaded punkt tokenizer.")

    def initialize(self):
        '''Reset the message interface. This is also called when restarting a dialog'''
        self.messages = []
        self.user_utterance_variables = []
        self.user_utterance_variables_without_full_names = []
        self.user_utterance_number = 0
        self.emit_fn('/history/user_utterance_variables',
                     self.user_utterance_variables_without_full_names)
        self.agent_utterance_variables = []
        self.agent_utterance_variables_without_full_names = []
        self.agent_utterance_number = 0
        self.emit_fn('/history/agent_utterance_variables',
                     self.agent_utterance_variables_without_full_names)
        self.emit_fn('/history/messages', self.messages)
        initial_message = copy.deepcopy(
            self.initial_message) if isinstance(self.agent, HumanAgent) else self.agent.initial_message()
        self.handle_message(copy.deepcopy(initial_message))

    def handle_message(self, message):
        '''
        :param msg: Looks like {
            'sender': 'user'|'agent',
            'body': 'text of latest message',
            'inputType': 'text' | 'speech',
            'template': 'something' (if sender is 'agent')
            'variables': 'something' (if sender is 'agent')
        }
        '''
        # Skip empty message
        if message is None: 
            return

        # Give the message a unique ID
        message['id'] = str(uuid4())

        # Translate the body of the message
        if self.user.language != self.agent.language and self.agent.language != '*':
            translated_message = self.translate_client.translate(
                message['body'],
                source_language=self.user.language,
                target_language=self.agent.language,
                format_="text")
            message['source_language'] = self.user.language
            message['target_language'] = self.agent.language
            message['translated_body'] = translated_message['translatedText']

        # Sender specific message handling
        if message['sender'] == 'user':
            self.handle_user_message(message)
        elif message['sender'] == "agent":
            self.handle_agent_message(message)
        elif message['sender'] == 'system':
            self.messages.append(message)
        else:
            raise ValueError("bad message sender, message %s" % str(message))

    def handle_user_message(self, message):
        self.user_utterance_number += 1
        # If user language is different from agent language, translate
        body = message.get('translated_body', message['body'])
        utterance = self._unescape_str(body)
        variable_group = 'u{}'.format(self.user_utterance_number)
        new_utterance_variables = {
            "variable_group": variable_group,
            "variables": [
                {"name": i, "value": word,
                    "full_name": "{}_{}".format(variable_group, i)}
                for i, word in enumerate(nltk.word_tokenize(self._unescape_str(utterance)))
            ]
        }
        self.emit_fn('/user_utterance_variables', new_utterance_variables)
        self.user_utterance_variables_without_full_names.append(
            copy.deepcopy(new_utterance_variables))
        self.user_utterance_variables.append(new_utterance_variables)
        add_full_names(self.user_utterance_variables[-1]["variables"],
                       self.user_utterance_variables[-1]["variable_group"])

        # We do a deepcopy here because we want to log the 'alternate_events' field,
        # but we need to delete the alternate events field below in order to emit it
        # in the socket.
        self.logger.log_user_utterance(
            copy.deepcopy(message), copy.deepcopy(
                new_utterance_variables['variables']))
        # agent utterance that was just logged
        breakdown_events = [self.logger.all_events[-1]]
        message["breakdown_events"] = [e.toJSON() for e in breakdown_events]
        self.messages.append(message)
        self.emit_fn('/message', message)

        if not isinstance(self.agent, HumanAgent):
            self.socket.start_background_task(self.send_agent_message, body)

    def handle_agent_message(self, message):
        self.agent_utterance_number += 1
        body = message.get('translated_body', message['body'])
        utterance = self._unescape_str(body)
        variable_group = 'a{}'.format(self.agent_utterance_number)
        new_utterance_variables = {
            "variable_group": variable_group,
            "variables": [
                {"name": i, "value": word,
                    "full_name": "{}_{}".format(variable_group, i)}
                for i, word in enumerate(nltk.word_tokenize(self._unescape_str(utterance)))
            ]
        }
        self.emit_fn('/agent_utterance_variables', new_utterance_variables)
        self.agent_utterance_variables_without_full_names.append(
            copy.deepcopy(new_utterance_variables))
        self.agent_utterance_variables.append(new_utterance_variables)
        add_full_names(self.agent_utterance_variables[-1]["variables"],
                       self.agent_utterance_variables[-1]["variable_group"])

        # We do a deepcopy here because we want to log the 'alternate_events' field,
        # but we need to delete the alternate events field below in order to emit it
        # in the socket.
        self.logger.log_agent_utterance(copy.deepcopy(message))
        # agent utterance that was just logged
        breakdown_events = [self.logger.all_events[-1]]
        for event in reversed(self.logger.all_events[:-1]):
            if isinstance(event, AgentUtteranceEvent):
                break
            if isinstance(event, APICallEvent) or isinstance(
                    event, EndDialogEvent):
                breakdown_events.append(event)

        breakdown_events.reverse()
        message["breakdown_events"] = [e.toJSON() for e in breakdown_events]

        self.messages.append(message)
        if 'alternate_events' in message:
            # We remove the 'alternate_events' field from the message
            # because alternates already contained in breakdown_events, so
            # we have no need for the redundancy in the frontend.
            #
            # Also, alternate events are of the AgentUtteranceClass, which
            # isn't implicitly JSON-serializable, so we can't emit it in the
            # socket.
            del message['alternate_events']

        self.emit_fn('/message', message)

        # Send back speech if necessary
        if self.input_type == 'speech':
            audio_content = text2speech.backend_process(message.get(
                'translated_body', message['body']), MessageInterface.LANGUAGE_CODES[self.user.language])
            self.emit_fn('/play_audio', audio_content)

        # Get the user's response
        if not isinstance(self.user, HumanUser):
            self.socket.start_background_task(self.send_user_message, body)

    def handle_connection(self, sender, request_variables, user_destination):
        self.emit_fn('/history/messages', self.messages)
        if sender == 'agent':
            self.emit_fn(
                '/history/user_utterance_variables',
                self.user_utterance_variables_without_full_names)
            self.emit_fn('/history/request_variables/agent', request_variables)
        elif sender == 'user':
            self.emit_fn(
                '/history/agent_utterance_variables',
                self.agent_utterance_variables_without_full_names)
            self.emit_fn(
                '/history/request_variables/user',
                [user_destination] if user_destination is not None else [])

    def send_user_message(self, message):
        user_response = self.user.on_message(message)
        if user_response is None:
            return
        else:
            self.handle_message(user_response)

    def send_agent_message(self, message, initial_alternate_events=None):
        # Cancel cancellable messages
        self.queued_events = set(
            ev for ev in self.queued_events if 'cancellable' not in ev or not ev['cancellable'])

        if initial_alternate_events is not None:
            agent_response = self.agent.on_message_with_alternate_events(
                tuple([e.toJSON() for e in self.logger.all_events]),
                initial_alternate_events)
        else:
            agent_response = self.agent.on_message(message, tuple(
                [e.toJSON() for e in self.logger.all_events]))

        if not agent_response:
            if any(isinstance(e, EndDialogEvent)
                   for e in reversed(self.logger.all_events)):
                body = "[END - DUMMY UTTERANCE] Click here and above to see breakdowns"
                agent_response = {
                    'body': body,
                    'template': body,
                    'variables': []
                }
            else:
                return

        if isinstance(agent_response, list):
            for m in agent_response:
                if m['body'] == '':
                    continue
                m['sender'] = 'agent'
                self.handle_message(m)
        else:
            if agent_response['body'] == '':
                return
            agent_response['sender'] = 'agent'
            hashable_agent_response = freeze(agent_response)

            if 'delay' in agent_response and agent_response['delay'] > 0:
                self.queued_events.add(hashable_agent_response)

                # this needs to be handled at the socket level to avoid
                # blocking the main thread
                self.socket.sleep(agent_response['delay'])
                if hashable_agent_response in self.queued_events:
                    self.handle_message(agent_response)
                    self.queued_events.remove(hashable_agent_response)
                # else: message has been de-queued

            else:
                self.handle_message(agent_response)

    def _unescape_str(self, s):
        if not isinstance(s, str):
            s = s[0]
        return s.replace("\\'", "'")
