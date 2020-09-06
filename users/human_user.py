from users.user import User


class HumanUser(User):
    def __init__(self, user_shared_state: dict, user_model_path: str, **kwargs):
        self.language = 'en'
        self.name = '008'
