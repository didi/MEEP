class MapsProvider():
    '''Skeleton class for a single map provider'''

    def find_place(self, query, latitude, longitude):
        """
        Returns a variable list, looks like:
        [
            {'name': latitude, 'value': 31.41324},
            ...
        ]
        """
        raise NotImplementedError

    def distance_matrix(self, source_latitude, source_longitude,
                        destination_latitude, destination_longitude):
        """
        Returns a variable list, looks like:
        [
            {'name': latitude, 'value': 31.41324},
            ...
        ]
        """
        raise NotImplementedError

    def places_nearby(self, query, latitude, longitude):
        """
        Returns a variable list with multiple objects, looks like:
        [
            {'name': '0', 'value': [
                {'name': 'latitude', 'value': 34.12341},
                ...
            ]},
            ...
        ]
        """
        raise NotImplementedError

    def load_variable(self, api_variables, variable_name):
        # DEPRECATED: use the version in backend/utils/utils.py instead of adding this to your class
        # This is retained for backward compatibility with python logs
        for variable in api_variables:
            if variable['name'] == variable_name:
                return variable['value']

    def __repr__(self):
        '''For executable logs to work, `repr` must generate an executable initialization of this class'''
        return 'MapProvider()'
