class Parameter():
    def __init__(self, name, is_query):
        self.name = name
        self.is_query = is_query


class API():
    def __init__(self, name, params):
        self.name = name
        self.params = params
