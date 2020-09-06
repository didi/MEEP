def create_user(user_class_name, user_shared_state, user_model_path, **kwargs):
    user_class_name = user_class_name if user_class_name is not None else 'users.human_user.HumanUser'
    module_name, _, class_name = user_class_name.rpartition('.')
    module = __import__(module_name, fromlist=[class_name])
    user_class = getattr(module, class_name)
    user = user_class(user_shared_state, user_model_path, **kwargs)
    user.class_name = user_class_name
    return user


class User():
    def __init__(self, user_shared_state: dict, user_model_path: str, **kwargs):
        self.user_shared_state = user_shared_state
        self.user_model_path = user_model_path
        self.language = '*' # supported language codes, e.g. 'en'

    def on_message(self, message: str) -> dict:
        '''
        Callback for a response to agent messages

        Args:
            message - text of the message to send (or prepare to send)

        Return:
        return a message of the following form OR a list of these which will be sent as separate messages:
        {
            'body': <message body> (str),
            'template': <template that was used> (str),
            'variables': <list of variables used in the template> (e.g. [v1_street_name, v2_city]),
            'alternate_events':  [OPTIONAL] list of logger.Event events that the agent *could* have taken instead of
                                 using the chosen template.  These may be API calls or different templates.
            'sender': Should always make this field 'user'

            # Delaying or interruptable messages. Only supported if sending a single message
            'delay': <number of seconds to wait before sending this message> (str, optional)
            'cancellable': <whether this message should be cancelled if another message is received before delay finishes> (bool, optional)
        }
        '''
        raise NotImplementedError

    def reset(self):
        pass

    def on_dialog_finished(self, completed, correct):
        pass
