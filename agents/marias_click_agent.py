from agents.agent import Agent
from utils.utils import load_templates
import json
from collections import OrderedDict, namedtuple


class ActiveRequest:
    def __init__(self, text=None, params=(), request_type=None):
        self.text = text
        self.params = OrderedDict()
        for name in params:
            self.params[name] = None
        assert request_type in [None, "template", "api_call"]
        self.type = request_type

    def get_param_name(self, i):
        return list(self.params.items())[i][0]

    def clear(self):
        self.text = None
        self.params = OrderedDict()
        self.type = None


class MariasAgent(Agent):
    def __init__(self, agent_shared_state, _agent_model_path,
                 interfaces, domain="microworld", **kwargs):
        super().__init__(agent_shared_state, None, interfaces)
        self.map_api_interface = self.interfaces[0]
        self.language = "en"
        self.reset()

        domain_module = __import__('domains.{}.config'.format(domain, domain), globals(), locals(),
                                   ['{}_domain'.format(domain)])
        self.domain = getattr(domain_module, '{}_domain'.format(domain))

        self.template_buttons = OrderedDict()
        self.api_buttons = OrderedDict()
        self.request_var_buttons = OrderedDict()
        self.utterance_var_buttons = OrderedDict()

        self.MAX_BUTTONS = 1000
        self.MAX_SLOTS = 0

        self._get_templates()
        self._get_apis()

        self.active_request = ActiveRequest()
        self.action_map = []

    def on_message(self, message, events):
        self._get_request_vars(events)
        self._get_utterance_vars(events)

        self._render_driver_screen()

    def get_action_map(self):
        self.action_map = []
        '''
        First MAX_SLOTS buttons will be allocated to the active request slots
        Next 3 slots are allocated to Clear, Queue, and Send
        Then: template buttons > API buttons > request variables > utterance variables
        '''
        for i in range(self.MAX_SLOTS):
            if i < len(self.active_request.params):
                name = self.active_request.get_param_name(i)
                self.action_map.append(MariasAgent._wrap_action("active_slot_{}".format(name), None,
                                                                True, "active_slot"))
            else:
                self.action_map.append(MariasAgent._wrap_action("active_slot_padding".format(i), None,
                                                                False, "active_slot"))
        for name in ["Clear", "Queue", "Send"]:
            clickable = True
            if not self.active_request.type:
                clickable = False
            if name == "Queue" and self.active_request.type == "api_call":
                clickable = False
            self.action_map.append(
                MariasAgent._wrap_action(
                    name, None, clickable, "active_button"))
        for name, value in self.template_buttons.items():
            self.action_map.append(
                MariasAgent._wrap_action(
                    name, value, True, "template"))
        for name, value in self.api_buttons.items():
            self.action_map.append(
                MariasAgent._wrap_action(
                    name, value, True, "api_call"))
        for name, value in self.request_var_buttons.items():
            self.action_map.append(
                MariasAgent._wrap_action(
                    name, value, True, "variable"))
        for name, value in self.utterance_var_buttons.items():
            self.action_map.append(
                MariasAgent._wrap_action(
                    name, value, True, "variable"))
        num_buttons = len(self.action_map)
        for i in range(self.MAX_BUTTONS - num_buttons):
            self.action_map.append(
                MariasAgent._wrap_action(
                    "var_padding", None, False, "variable"))

    @staticmethod
    def _wrap_action(name, value, clickable, action_type):
        assert action_type in [
            None,
            "active_slot",
            "active_button",
            "template",
            "api_call",
            "variable"]
        return {
            "name": name,
            "value": value,
            "clickable": clickable,
            "type": action_type
        }

    def take_action(self, action_idx):
        action = self.action_map[action_idx]
        if action.type == "template":
            self.active_request = ActiveRequest(
                action["name"], action["value"], "template")
        elif action.type == "api_call":
            self.active_request = ActiveRequest(
                action["name"], action["value"], "api_call")
        else:
            # TODO: implement highlighting for selected slot, populating slot,
            # sending/queueing message
            pass

    def _get_request_vars(self, events):
        for var_name, var_value in self.initial_variables.items():
            self.request_var_buttons["source_" + var_name] = str(var_value)
        for event in events:
            if event["event_type"] == "api_call":
                for var in event["params"]:
                    self.request_var_buttons[var["full_name"]] = str(
                        var["value"])

    def _get_templates(self):
        template_file = getattr(self.domain, 'agent_templates')
        for group in load_templates(template_file):
            for t in group["templates"]:
                self.template_buttons[t["template"]] = t["params"]
                if len(t["params"]) > self.MAX_SLOTS:
                    self.MAX_SLOTS = len(t["params"])

    def _get_apis(self):
        with open(self.domain.apis) as f:
            api_list = json.load(f)
        for api in api_list:
            self.api_buttons[api["name"]] = [par["name"]
                                             for par in api["params"]]
            if len(api["params"]) > self.MAX_SLOTS:
                self.MAX_SLOTS = len(api["params"])

    def _get_utterance_vars(self, events):
        for event in events:
            if event["event_type"] == "user_utterance":
                for var in event["variables"]:
                    self.utterance_var_buttons[var["full_name"]] = str(
                        var["value"])

    def _render_driver_screen(self):
        print("============ BEGIN DRIVER SCREEN ============")
        print("ACTIVE REQIEST:")
        print("\t" + str(self.active_request))
        print("TEMPLATES:")
        for button in self.template_buttons:
            print("\t" + button)
        print("APIS:")
        for button in self.api_buttons:
            print("\t" + button)
        print("REQUEST VARS:")
        for name, value in self.request_var_buttons.items():
            print("\t{}={}".format(name, value))
        print("UTTERANCE VARS:")
        for name, value in self.utterance_var_buttons.items():
            print("\t{}={}".format(name, value))
        print("============ END DRIVER SCREEN ============")

    def initial_message(self):
        return super().initial_message()

    def on_message_with_alternate_events(
            self, events, initial_alternate_events=None):
        super().on_message_with_alternate_events(
            source, events, initial_alternate_events)
