def create_agent(agent_class_name, agent_shared_state,
                 agent_model_path, interfaces, domain, **kwargs):
    agent_class_name = agent_class_name if agent_class_name is not None else 'agents.human_agent.HumanAgent'
    module_name, _, class_name = agent_class_name.rpartition('.')
    module = __import__(module_name, fromlist=[class_name])
    agent_class = getattr(module, class_name)
    agent = agent_class(
        agent_shared_state,
        agent_model_path,
        interfaces,
        domain,
        **kwargs)
    agent.class_name = agent_class_name
    return agent


class Agent():
    def __init__(self, agent_shared_state: dict,
                 agent_model_path: str, interfaces: list,
                 domain, **kwargs):
        '''
        Args:
            agent_shared_state - Shared state for a single model used across multiple parallel
                                 session "rooms".
            agent_model_path - File/Dir to load models and configs from
                               Some agents like the rule-based model may not require a model file
            interfaces - Interfaces from different domains like "maps" or "weather" that specify which
                         which APIs and NLG templates are loaded
            domain - Instance of domains.Domain
            **kwargs - Additional parameters from app_factory or room. Constant parameters should be provided in the model file instead
        '''
        self.agent_shared_state = agent_shared_state
        self.agent_model_path = agent_model_path
        self.interfaces = interfaces
        self.language = '*'  # supported language codes, e.g. 'en'
        self.name = self.__class__.__name__
        self.initial_variables = None

    def on_message(self, message: str, events: dict) -> dict:
        '''
        Callback for a response to user messages

        Args:
            message - text of the message to send (or prepare to send)
            events - an object containing the variables returned by API calls

            See agents/README.md or /dataset/examples/log_60.json for examples of the parameter format

        Return:
        return a message of the following form OR a list of these which will be sent as separate messages:
        {
            'body': <message body> (str),
            'template': <template that was used> (str),
            'variables': <list of variables used in the template> (e.g. [v1_street_name, v2_city]),
            'alternate_events':  [OPTIONAL] list of logger.Event events that the agent *could* have taken instead of
                                 using the chosen template.  These may be API calls or different templates.

            # Delaying or interruptable messages. Only supported if sending a single message
            'delay': <number of seconds to wait before sending this message> (str, optional)
            'cancellable': <whether this message should be cancelled if another message is received before delay finishes> (bool, optional)
        }
        '''
        raise NotImplementedError

    def on_message_with_alternate_events(
            self, events, initial_alternate_events=None):
        ''' Optional implementation: This is an experimental version of on_message() that adds
            initial_alternate_events as additional context before predicting the next action. '''
        raise NotImplementedError

    def initial_message(self):
        """
        Return the initial greeting message that the agent should send
        Returns a message of the form:
        {
            'body': <message body> (str),
            'template': <template that was used> (str),
            'variables': <list of variables used in the template> (e.g. [v1_street_name, v2_city])
        }
        """
        greeting = "Hello! Where would you like to go today?"
        return {
            'body': greeting,
            'template': greeting,
            'variables': [],
            'sender': 'agent',
        }

    def reset(self, initial_variables: dict):
        '''
        Reset internal state between dialogs
        Args:
            initial_variables - key-value pairs containing the initial variables (see manager.py:get_initial_variables)
        '''
        self.initial_variables = initial_variables

    def on_dialog_finished(self, completed: bool, correct: bool):
        '''
        Called at the end of a dialog
        '''
        pass
