from functools import wraps
import inspect
import traceback

from flask import jsonify, request
from apis.utils import add_full_names

import sys
import os
sys.path.append(
    os.path.join(
        os.path.dirname(
            os.path.dirname(__file__)),
        "gui/backend/logger"))


def webhook_input_format(request_json):
    query_result = request_json.get('queryResult', {})
    pass


def webhook_output_format(request_json):
    pass


def webhook_endpoint_format(endpoint):
    return "/webhook" + endpoint


def wrap_name():
    def inner(f):
        f.__name__ = f.__name__ + '_webhook'
        return f
    return inner


class BaseInterface():
    '''Generic API interface'''

    def __init__(self):
        # Should be set by classes that extend this
        self.provider = None

    def create_endpoints(self, app, rooms):
        '''Automatically create flask endpoints for functions decorated with @route'''
        for _name, fcn in inspect.getmembers(type(self)):
            if hasattr(fcn, 'endpoint'):
                self.flask_wrap(
                    app,
                    fcn,
                    fcn.endpoint,
                    rooms,
                    **fcn.flask_kwargs)

    def flask_wrap(self, app, fcn, endpoint, rooms, **kwargs):
        '''
        Register a flask endpoint for an API interface and
        convert data to and from json

        app - a flask app
        fcn - the function exposed by the API interface. should take (self, request_params) as arguments
        endpoint - the URL for this function (str)
        '''
        endpoint = '/<room_id>' + endpoint

        @app.route(endpoint, **kwargs)
        @wraps(fcn)
        def wrapped(room_id):
            room = rooms[room_id]
            self.manager = room.manager
            return jsonify(fcn(self, request.json))

        @app.route(webhook_endpoint_format(endpoint), **kwargs)
        @wrap_name()
        @wraps(fcn)
        def webhook_wrapped(room_id):
            return jsonify(webhook_output_format(
                fcn(self, webhook_input_format(request.json))))

    def api_call(self, fcn, request_params, *args,
                 alternate_events=None, **kwargs):
        '''
        Call an API and do logging

        APIs should return an object that look like:
        [{'name': "abc", 'value': 123}]
        '''

        # Make the API call
        try:
            variables = fcn(*args, **kwargs)
        except Exception as e:
            variables = [{
                'name': 'error',
                'value': str(e),
            },
            {
                'name': 'traceback',
                'value': traceback.format_exc()
            }]

        # Update saved variable state
        self.manager.request_number += 1
        variable_group = "v{}".format(self.manager.request_number)
        add_full_names(variables, variable_group)
        response = {
            "variable_group": variable_group,
            "variable_group_api_call": "{}({})".format(fcn.__name__, ", ".join(map(repr, args))),
            "variables": variables
        }
        self.manager.request_variables.append(response)

        # Log and save variables to the backend
        if self.manager._logger:
            self.manager._logger.log_api_call(
                type(
                    self.provider).__name__,
                fcn.__name__,
                request_params,
                variables,
                alternate_events)

        # Send variables to the frontend
        self.manager.emit('/request_variables/agent', response)

        return response
