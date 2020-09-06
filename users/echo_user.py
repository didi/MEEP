from users.user import User


class EchoUser(User):
    def __init__(self, user_shared_state: dict, user_model_path: str, **kwargs):
        super().__init__(user_shared_state, user_model_path)
        self.language = 'en'

    def on_message(self, message):
        return {
            'body': message,
            'sender': 'user',
        }
