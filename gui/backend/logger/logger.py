from copy import deepcopy
import json
import os
import shutil
import time
from utils.utils import snake_case


def escape_str(s):
    return s.replace("'", "\\'").replace('"', '\\"')


def format_variable(v):
    if isinstance(v, str):
        return "'{}'".format(escape_str(v))
    else:
        return str(v)


class Logger():
    def __init__(self, interfaces, room_id, initial_variables, log_path='logs', agent_name=None, purge_every_N=0):
        self.all_events = []
        self.interfaces = interfaces
        self.initial_variables = initial_variables
        self.log_path = log_path
        self.agent_name = agent_name if agent_name is not None else '007'
        self.start_time = None
        self.filename = None
        self.room_id = room_id
        self.purge_every_N = purge_every_N  # Purge log directory every N logs

    def log_agent_utterance(self, message):
        if len(self.all_events) == 0:
            self.start_time = time.time()
        self.all_events.append(AgentUtteranceEvent(message))

    def log_user_utterance(self, message, variables):
        if len(self.all_events) == 0:
            self.start_time = time.time()
        self.all_events.append(UserUtteranceEvent(message, variables))

    def log_api_call(self, provider_name, endpoint, params,
                     variables, alternate_events=None):
        if len(self.all_events) == 0:
            self.start_time = time.time()
        self.all_events.append(
            APICallEvent(
                provider_name,
                endpoint,
                params,
                variables,
                alternate_events))

    def log_end_dialog(self, user_ended_dialog, success):
        if len(self.all_events) == 0:
            self.start_time = time.time()
        self.all_events.append(EndDialogEvent(user_ended_dialog, success))
        if self.filename is None:
            self.filename = self.get_filename()

    def get_filename(self):
        '''Get next available log number'''
        if self.log_path is None:
            return None
        os.makedirs(self.log_path, exist_ok=True)
        files = os.listdir(self.log_path)
        i = 0

        while any('log_{}.{}'.format(i, extension)
                  in files for extension in ('txt', 'py', 'json')):
            i += 1

        if self.purge_every_N > 0 and i > self.purge_every_N:
            shutil.rmtree(self.log_path, ignore_errors=True)
            os.makedirs(self.log_path, exist_ok=True)
            i = 0

        # Create empty files
        filename = os.path.join(
            os.path.abspath(
                self.log_path),
            'log_{}'.format(i))
        for extension in ('txt', 'py', 'json'):
            with open(filename + '.' + extension, 'w') as f:
                pass
        return filename

    def save_logs(self, correct, agent_name, user_story):
        if not any(isinstance(event, EndDialogEvent)
                   for event in reversed(self.all_events)):
            if len(self.all_events) == 0:
                self.start_time = time.time()
            self.all_events.append(EndDialogEvent(user_ended_dialog=True))

        if self.all_events and isinstance(self.all_events[-1], AgentUtteranceEvent) and \
           self.all_events[-1].message.get("body", "").startswith("[END - DUMMY UTTERANCE]"):
            self.all_events = self.all_events[:-1]

        if self.start_time is None:
            self.start_time = time.time()

        new_filename = self.get_filename() if self.filename is None else self.filename
        self.filename = None

        # Generate log
        duration = time.time() - self.start_time
        dialog_event = DialogEvent(
            self.interfaces,
            self.initial_variables,
            self.all_events,
            agent_name,
            duration,
            correct,
            user_story)

        exe_log = dialog_event.save_executable_log()
        with open(new_filename + ".py", 'w') as f:
            for line in exe_log:
                f.write(line + '\n')
        text_log = dialog_event.save_text_log()
        with open(new_filename + ".txt", 'w') as f:
            for line in text_log:
                f.write(line + '\n')
        json_log = dialog_event.save_json_log()
        with open(new_filename + ".json", 'w') as f:
            json.dump(json_log, f, indent=2)

        self.all_events[:] = []

        return new_filename


class Event():
    def __init__(self):
        pass

    def save_executable_log(self):
        raise NotImplementedError

    def save_text_log(self):
        raise NotImplementedError

    def toJSON(self):
        raise NotImplementedError

    def toJSON_clean(self):
        return self.toJSON()


class WaitForUserEvent(Event):
    def save_executable_log(self):
        pass

    def save_text_log(self):
        pass

    def toJSON(self):
        return {"event_type": "wait_for_user"}


class UserUtteranceEvent(Event):
    def __init__(self, message, utterance_variables):
        if 'alternate_events' not in message:
            message['alternate_events'] = {
                'active_index': 0,
                'failed_indexes': [],
                'events': [
                    {
                        "event_type": "user_utterance",
                        "utterance": message['body']
                    },
                    WaitForUserEvent().toJSON()]
            }
        self.message = message
        self.utterance_variables = utterance_variables

    def save_executable_log(self):
        # Save user utterance variables
        log = []
        log.append("")
        log.append("# User utterance")
        log.append(
            "print('User: {}')".format(
                escape_str(
                    self.message['body'])))
        for variable in self.utterance_variables:
            log.append(
                "{} = {}".format(
                    variable['full_name'],
                    format_variable(
                        variable['value'])))
        return log

    def save_text_log(self):
        log = []
        log.append("USER: {}".format(self.message['body']))
        if 'translated_body' in self.message:
            log.append(
                "USER (translated): {}".format(
                    self.message['translated_body']))
        return log

    def toJSON_helper(self, clean=False):
        log = {
            "event_type": "user_utterance",
            "utterance": self.message['body'],
            "variables": self.utterance_variables,
        }
        if not clean:
            log["alternate_events"] = self.message['alternate_events']
        if 'source_language' in self.message:
            log['source_language'] = self.message['source_language']
        if 'target_language' in self.message:
            log['target_language'] = self.message['target_language']
        if 'translated_body' in self.message:
            log['translated_body'] = self.message['translated_body']
        if 'id' in self.message:
            log['id'] = self.message['id']
        return log

    def toJSON(self):
        return self.toJSON_helper(clean=False)

    def toJSON_clean(self):
        return self.toJSON_helper(clean=True)


class AgentUtteranceEvent(Event):
    def __init__(self, message):
        if 'alternate_events' not in message:
            message['alternate_events'] = {
                'active_index': 0,
                'failed_indexes': [],
                'events': [
                    {
                        "event_type": "agent_utterance",
                        "utterance": message['body'],
                        "template": message['template'],
                        "params": message['variables']
                    },
                    WaitForUserEvent().toJSON()]
            }

        self.message = message

    def save_executable_log(self):
        log = []
        log.append("")
        log.append("# Agent utterance")
        variables = ", ".join(self.message['variables'])
        log.append("print('Agent: {}'.format({}))".format(
            escape_str(self.message['template']), variables))
        return log

    def save_text_log(self):
        log = []
        log.append("AGENT: {}".format(self.message['body']))
        if 'translated_body' in self.message:
            log.append(
                "AGENT (translated): {}".format(
                    self.message['translated_body']))
        return log

    def toJSON_helper(self, clean=False):
        log = {
            "event_type": "agent_utterance",
            "utterance": self.message['translated_body'] if 'translated_body' in self.message else self.message['body'],
            "template": self.message['template'],
            "params": self.message['variables'],
        }
        if 'source_language' in self.message:
            log['source_language'] = self.message['source_language']
        if 'target_language' in self.message:
            log['target_language'] = self.message['target_language']
        if 'translated_body' in self.message:
            log['translated_body'] = self.message['translated_body']
        if 'alternate_events' in self.message and \
                (not clean or len(self.message['alternate_events'].get("events", [])) > 2):
            # By default alternate events always has at least 2 events: the original event and
            # the wait_for_user_event.
            log['alternate_events'] = deepcopy(
                self.message["alternate_events"])
            log['alternate_events']['events'] = [
                e for e in self.message['alternate_events']['events']]
        if "id" in self.message:
            log["id"] = self.message['id']
        return log

    def toJSON(self):
        return self.toJSON_helper(clean=False)

    def toJSON_clean(self):
        return self.toJSON_helper(clean=True)


class APICallEvent(Event):
    def __init__(self, provider_name, endpoint, params,
                 variables, alternate_events=None):
        # convert ClassName to a variable_name for readability
        self.provider_variable_name = snake_case(provider_name)
        self.endpoint = endpoint
        self.params = params
        self.variables = variables

        if alternate_events is None:
            alternate_events = {
                'active_index': 0,
                'failed_indexes': [],
                'events': [
                    {
                        "event_type": "api_call",
                        "endpoint": self.endpoint,
                        "params": self.params,
                        "variables": []
                    },
                    WaitForUserEvent().toJSON()]
            }
        self.alternate_events = alternate_events

    def save_variable(self, v, i, api_variables="api_variables"):
        if isinstance(v['value'], list):
            result = tuple()
            for inner_i, inner_v in enumerate(v['value']):
                result += self.save_variable(
                    inner_v,
                    inner_i,
                    api_variables=api_variables +
                    "[{}]['value']".format(i))
            return result
        else:
            return ("{} = load_variable({}, '{}')".format(
                v['full_name'], api_variables, v['name']),)

    def save_executable_log(self):
        log = []

        log.append("")
        log.append("# API call")

        # Save the API call
        params = ", ".join([p.get('variable_name', 'var')
                            for p in self.params])
        log.append(
            "api_variables = {}.{}({})".format(
                self.provider_variable_name,
                self.endpoint,
                params))

        # Save the code to read the variables back
        if self.variables is not None:
            for i, variable in enumerate(self.variables):
                log += self.save_variable(variable, i)

        return log

    def save_text_log(self):
        log = []
        params = ", ".join([p.get('variable_name', 'var')
                            for p in self.params])
        log.append("API_CALL: {}({})".format(self.endpoint, params))
        return log

    def toJSON_helper(self, clean=False):
        out = {
            "event_type": "api_call",
            "endpoint": self.endpoint,
            "params": self.params,
            "variables": self.variables,
        }
        if self.alternate_events and \
                (not clean or len(self.alternate_events.get("events", [])) > 2):
            # By default alternate events always has at least 2 events: the original event and
            # the wait_for_user_event.
            out["alternate_events"] = deepcopy(self.alternate_events)
            out["alternate_events"]["events"] = [
                e for e in self.alternate_events["events"]]
        return out

    def toJSON(self):
        return self.toJSON_helper(clean=False)

    def toJSON_clean(self):
        return self.toJSON_helper(clean=True)


class EndDialogEvent(Event):
    '''
    Event created when the dialog is ended for any reason. This should be the last event.
    When using our frontend, the following combinations are possible:

    user_ended_dialog | success | when?
    0 | 0 | agent selects give_up or any other api with @completes_dialog(success=False)
    1 | 0 | user selects end_dialog
    0 | 1 | agent selects end_dialog or any api with @completes_dialog(success=True)
    1 | 1 | not possible
    '''

    def __init__(self, user_ended_dialog=False, success=False):
        self.user_ended_dialog = user_ended_dialog
        self.success = success

        self.report_string = (
            ('User' if user_ended_dialog else 'Agent')
            + ' ended dialog '
            + ('successfully' if success else 'unsuccessfully')
        )

    def save_executable_log(self):
        return ["print('{}')".format(self.report_string)]

    def save_text_log(self):
        return [self.report_string]

    def toJSON(self):
        json = {
            "event_type": "end_dialog",
            # this indicates that the dialog was marked completed by the agent,
            # but not that the result was correct
            "success": self.success,
            "user_ended_dialog": self.user_ended_dialog,
        }
        return json


class DialogEvent(Event):
    def __init__(self, interfaces, initial_variables, all_events,
                 agent_name, duration, correct, user_story):
        self.interfaces = interfaces
        self.initial_variables = initial_variables
        self.all_events = deepcopy(all_events)
        self.agent_name = agent_name
        self.duration = duration
        self.correct = correct
        self.user_story = user_story

    def save_executable_log(self):
        log = []
        log.append("## Setup")
        log.append("from utils.utils import load_variable")
        log.append("from keys import keys")
        for interface in self.interfaces:
            provider_class_name = type(interface.provider).__name__
            provider_variable_name = snake_case(provider_class_name)

            log.append("from apis import {}".format(provider_class_name))
            log.append(
                "{} = {}".format(
                    provider_variable_name, repr(
                        interface.provider)))

        log.append("")
        log.append("print('Agent name: {}')".format(self.agent_name))

        log.append("")
        log.append("## Initial variables")
        for variable in self.initial_variables['variables']:
            log.append(
                "{} = {}".format(
                    variable['full_name'],
                    format_variable(
                        variable['value'])))

        log.append("")
        log.append("## Events")
        for event in self.all_events:
            log += event.save_executable_log()

        log.append("## Correct result? {}".format(self.correct))
        log.append("print('Correct result? {}')".format(self.correct))
        return log

    def save_text_log(self):
        log = []
        log.append("Agent name: {}".format(self.agent_name))
        log.append("")

        log.append("# Initial variables")
        for variable in self.initial_variables['variables']:
            log.append(
                "{} = {}".format(
                    variable['full_name'],
                    format_variable(
                        variable['value'])))
        log.append("")

        for event in self.all_events:
            log += event.save_text_log()
        log.append("Duration: {}s".format(self.duration))
        log.append("Correct result? {}".format(self.correct))
        return log

    def save_json_log(self):
        logs = {
            'agent_name': self.agent_name,
            'initial_variables': self.initial_variables,
            'interfaces': [repr(interface.provider) for interface in self.interfaces],
            'duration': self.duration,
            # retained for backward compatibility with existing datasets. Do
            # not use
            'correct_destination': self.correct,
            'correct': self.correct,
            'events': [event.toJSON_clean() for event in self.all_events],
            'user_story': self.user_story if self.user_story else {}
        }

        return logs
