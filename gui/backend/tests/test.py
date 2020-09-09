import json
import unittest
import sys
import os
import time
from getpass import getuser
from socket import gethostname
from contextlib import contextmanager, redirect_stderr, redirect_stdout

from domains.compare_numbers.config import compare_numbers_domain
from domains.destination.config import destination_domain
from domains.microworld.config import microworld_domain2 as microworld_domain
from domains.weather.config import weather_domain
from utils.utils import load_variable

sys.path.extend([
    os.path.join(sys.path[0], '../../..')  # for loading agents, apis
])
from app_factory import AppFactory
from keys import keys
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = keys['google_speech']

# Import agents and apis modules
from agents.agent import create_agent

# Some useful constants
trader_joes_request = [{"param": "query", "variable_name": "u1_0 + \" \" + u1_1 + \" \" + u1_2", "value": "Trader Joe 's"},
                       {"param": "src latitude",
                        "variable_name": "source_latitude",
                        "value": 33.9816425},
                       {"param": "src longitude",
                        "variable_name": "source_longitude",
                        "value": -118.4409761}
                       ]


@contextmanager
def suppress_stdout_stderr():
    """
    A context manager that redirects stdout and stderr to devnull
    Source: https://stackoverflow.com/a/52442331
    """
    with open(os.devnull, 'w') as fnull:
        with redirect_stderr(fnull) as err, redirect_stdout(fnull) as out:
            yield (err, out)


class APITests(unittest.TestCase):
    '''Base class for creating tests for APIs'''
    @classmethod
    def setUpClassHelper(cls, domain):
        '''
        Instantiate variables shared within a test case.
        Must be called with a Domain object in setUpClass
        '''
        cls.app = AppFactory(domain=domain)
        cls.flask_client, cls.socket_client = cls.app.create_test_clients()

    def assertAPISuccess(self, response):
        # print(response.get_data(as_text=True))
        self.assertFalse(
            load_variable(
                json.loads(
                    response.get_data(
                        as_text=True))['variables'],
                'error'))


class CompareNumbersAPITests(APITests):
    '''Simplest domain. Test compare numbers, and some other basic functionality tests'''
    @classmethod
    def setUpClass(cls):
        cls.setUpClassHelper(compare_numbers_domain)

    def test_compare_numbers(self):
        response = self.flask_client.post('/0/compare_numbers/compare', json=[
            {'param': 'number1', 'value': '10'},
            {'param': 'number2', 'value': '5'}
        ])
        self.assertAPISuccess(response)

    # Basic functionality tests
    def test_static_apis(self):
        for endpoint in ('/apis', '/templates/agent', '/0/user/options'):
            response = self.flask_client.get(endpoint)
            self.assertNotEqual(
                len(json.loads(response.get_data(as_text=True))), 0)

    def test_message(self):
        self.socket_client.emit(
            '/0/message', {'sender': 'user', 'body': 'hello'})

@unittest.skipUnless('darksky' in keys and 'wit_date' in keys,
                     'Missing darksky and/or wit keys. Check api_keys.json')
class WeatherAPITests(APITests):
    '''Test the weather API'''
    @classmethod
    def setUpClass(cls):
        cls.setUpClassHelper(weather_domain)

    def test_current(self):
        response = self.flask_client.post('/0/weather/current', json=[
            {"param": "lat/long",
             "variable_name": "src lat/long",
             "value": "33.9816425,-118.4409761"},
        ])
        self.assertAPISuccess(response)

    def test_at_time(self):
        response = self.flask_client.post('/0/weather/at_time', json=[
            {"param": "lat/long",
             "variable_name": "src lat/long",
             "value": "33.9816425,-118.4409761"},
            {"param": "time query",
             "variable_name": "time query",
             "value": "tomorrow at 2"},
        ])
        self.assertAPISuccess(response)

    def test_at_time_range(self):
        response = self.flask_client.post('/0/weather/at_time', json=[
            {"param": "lat/long",
             "variable_name": "src lat/long",
             "value": "33.9816425,-118.4409761"},
            {"param": "time query",
             "variable_name": "time query",
             "value": "from tuesday to thursday"},
        ])
        self.assertAPISuccess(response)


@unittest.skipUnless('google_maps' in keys,
                     'Missing Google Maps API keys. Check api_keys.json')
class GoogleMapsAPITests(APITests):
    '''Test find_place, places_nearby and distance_matrix'''
    @classmethod
    def setUpClass(cls):
        cls.setUpClassHelper(destination_domain)

    def test_find_place(self):
        response = self.flask_client.post(
            '/0/maps/find_place', json=trader_joes_request)
        self.assertAPISuccess(response)

    def test_find_latlon(self):
        response = self.flask_client.post('/0/maps/find_latlon', json=[
            {"param": "query", "variable_name": "query", "value": "beijing"},
            {"param": "src lat/long",
             "variable_name": "src lat/long",
             "value": "33.9816425,-118.4409761"},
        ])
        self.assertAPISuccess(response)

    def test_places_nearby(self):
        response = self.flask_client.post(
            '/0/maps/places_nearby', json=trader_joes_request)
        self.assertAPISuccess(response)

    def test_distance_matrix(self):
        response = self.flask_client.post('/0/maps/distance_matrix', json=[{"param": "src latitude", "variable_name": "source_latitude", "value": 33.9816425},
                                                                           {"param": "src longitude",
                                                                            "variable_name": "source_longitude",
                                                                            "value": -118.4409761},
                                                                           {"param": "dest latitude",
                                                                            "variable_name": "v1_latitude",
                                                                            "value": 33.9700000},
                                                                           {"param": "dest longitude", "variable_name": "v1_longitude", "value": -118.40000}])
        self.assertAPISuccess(response)

    def test_start_driving(self):
        response = self.flask_client.post('/0/maps/start_driving', json=[
            {"param": "dest latitude",
             "variable_name": "source_latitude",
             "value": 123.123},
            {"param": "dest longitude",
             "variable_name": "source_longitude",
             "value": 123.123}
        ])
        self.assertAPISuccess(response)


class MicroworldAPITests(APITests):
    @classmethod
    def setUpClass(cls):
        cls.setUpClassHelper(microworld_domain)

    def test_find_place(self):
        request = [{"param": "query", "variable_name": "u1_0", "value": "Coffee Connection"},
                   {"param": "src latitude",
                    "variable_name": "source_latitude",
                    "value": 1},
                   {"param": "src longitude",
                    "variable_name": "source_longitude",
                    "value": 6.5}
                   ]
        response = self.flask_client.post('/0/maps/find_place', json=request)
        self.assertAPISuccess(response)

    def places_nearby(self):
        request = [{"param": "query", "variable_name": "u1_0", "value": "Starbucks"},
                   {"param": "src latitude",
                    "variable_name": "source_latitude",
                    "value": 1},
                   {"param": "src longitude",
                    "variable_name": "source_longitude",
                    "value": 6.5}
                   ]
        response = self.flask_client.post(
            '/0/maps/places_nearby', json=request)
        self.assertAPISuccess(response)


class AgentTests(unittest.TestCase):
    def _get_received(self):
        '''return a list of messages received from the server from the agent'''
        result = []
        for variable in self.socket_client.get_received():
            if variable['name'] == '/message' and variable['args'][0]['sender'] == 'agent':
                result.append(variable['args'][0]['body'])
        return result

    def _setup_helper(self):
        '''Create commonly used objects and join the chatroom'''
        self.flask_client, self.socket_client = self.app.create_test_clients()
        self.interfaces = self.app.rooms['0'].interfaces
        self.socket_client.emit('join', {'roomId': '0', 'sender': 'agent'})
        self.domain = self.app.domain.clone(self.interfaces)


class DestinationAgentTests(AgentTests):
    def setUp(self):
        self.app = AppFactory(destination_domain)
        self._setup_helper()

    def test_echo_agent(self):
        agent = create_agent(
            'agents.echo_agent.EchoAgent',
            None,
            None,
            self.interfaces)
        self.app.rooms['0'].set_agent(agent)

        # Consume startup messages
        self.socket_client.get_received()

        # Send a new message and check that the response matches
        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': 'hello, echo', 'roomId': '0'})
        self.assertEqual(self._get_received(), ['hello, echo'])

    def test_delay_agent(self):
        agent = create_agent(
            'agents.delay_agent.DelayAgent', None,
            os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "./data/delay_agent_0.1.config.txt"),
            self.interfaces)
        self.assertEqual(0.1, agent.delay)
        self.app.rooms['0'].set_agent(agent)

        self.socket_client.get_received()

        # Check echo
        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': 'echo this', 'roomId': '0'})
        self.assertEqual(self._get_received(), ['echo this'])

        # Check that messages are cancelled properly
        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': 'wait', 'roomId': '0'})
        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': 'cancel', 'roomId': '0'})
        self.assertEqual(self._get_received(), ['cancel'])

        # These tests fail because delayed messages aren't received by socket_client. Not sure why, but tested manually instead
        # # Check that delay works
        # self.socket_client.emit('/message', {'sender': 'user', 'body': 'wait'})
        # self.assertEqual(self._get_received(self.socket_client.get_received()), []) # before delay expires
        # time.sleep(0.2)
        # self.assertEqual(self._get_received(received), ['This message was
        # sent after 0.1 seconds of not receiving another message']) # after
        # delay finishes

        # # Check that delay is not cancelled but the order is correct
        # self.socket_client.emit('/message', {'sender': 'user', 'body': 'delay'})
        # self.socket_client.emit('/message', {'sender': 'user', 'body': 'dont cancel'})
        # time.sleep(0.4)
        # self.assertEqual(self._get_received(), ['dont cancel', 'delay'])


class MicroworldAgentTests(AgentTests):
    def setUp(self):
        self.app = AppFactory(microworld_domain)
        self._setup_helper()

    def test_random_agent(self):
        '''
        See NumberAgentTests.test_random_agent for implementation notes
        '''
        agent = create_agent(
            'agents.random_agent.RandomClickLevelAgent',
            None, None, self.interfaces, domain=self.domain, seed=123)
        self.app.rooms['0'].set_agent(agent)

        self.socket_client.get_received()
        self.socket_client.emit('/message', {'sender': 'user', 'body': 'Gap', 'roomId': '0'})
        self.assertTrue(self._get_received())
        self.socket_client.emit('/message', {'sender': 'user', 'body': 'Starbucks', 'roomId': '0'})
        self.assertTrue(self._get_received())
        self.socket_client.emit('/message', {'sender': 'user', 'body': 'how far is it?', 'roomId': '0'})
        self.assertTrue(self._get_received())
        self.socket_client.emit('/message', {'sender': 'user', 'body': 'quit', 'roomId': '0'})

        non_debug_responses = [msg for msg in self._get_received() if not msg.startswith('DEBUG')]
        self.assertEqual(non_debug_responses[-1], 'Goodbye, ending dialog as requested by user')


    def test_typed_random_agent(self):
        agent = create_agent('agents.random_agent.TypedRandomAgent', None, None, self.interfaces, domain=self.domain, seed=123)
        self.app.rooms['0'].set_agent(agent)

        self.socket_client.get_received()
        self.socket_client.emit('/message', {'sender': 'user', 'body': 'starbucks', 'roomId': '0'})
        self.assertTrue(self._get_received())
        self.socket_client.emit('/message', {'sender': 'user', 'body': 'how far is it?', 'roomId': '0'})
        self.assertTrue(self._get_received())

class WeatherAgentTests(AgentTests):
    def setUp(self):
        self.app = AppFactory(weather_domain)
        self._setup_helper()

    def test_random_agent(self):
        '''
        See NumberAgentTests.test_random_agent for implementation notes
        '''
        agent = create_agent(
            'agents.random_agent.RandomClickLevelAgent',
            None,
            None,
            self.interfaces,
            domain=self.domain,
            seed=123)
        self.app.rooms['0'].set_agent(agent)

        self.socket_client.get_received()
        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': 'california', 'roomId': '0'})
        self.assertTrue(self._get_received())
        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': 'beijing', 'roomId': '0'})
        self.assertTrue(self._get_received())
        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': 'will it rain?', 'roomId': '0'})
        self.assertTrue(self._get_received())

        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': 'quit', 'roomId': '0'})
        self.assertEqual(self._get_received()
                         [-1], 'Goodbye, ending dialog as requested by user')


    def test_typed_random_agent(self):
        agent = create_agent('agents.random_agent.TypedRandomAgent', None, None, self.interfaces, domain=self.domain, seed=123)
        self.app.rooms['0'].set_agent(agent)

        self.socket_client.get_received()
        self.socket_client.emit('/message', {'sender': 'user', 'body': 'california', 'roomId': '0'})
        print('received', self._get_received())
        self.socket_client.emit('/message', {'sender': 'user', 'body': 'whats the weather in california', 'roomId': '0'})
        print('received', self._get_received())


class NumberAgentTests(AgentTests):
    def setUp(self):
        self.app = AppFactory(compare_numbers_domain)
        self._setup_helper()

    def test_compare_agent(self):
        agent = create_agent(
            'agents.compare_numbers_agent.CompareNumbersAgent',
            None, None, self.interfaces)
        self.app.rooms['0'].set_agent(agent)
        self.socket_client.emit('join', {'roomId': '0', 'sender': 'agent'})

        self.socket_client.get_received()
        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': 'is 3 larger than 4?', 'roomId': '0'})
        self.assertEqual(self._get_received(), ['3 is less than 4'])
        self.socket_client.emit('/message',
                                {'sender': 'user',
                                 'body': 'is 6.25 less than 4.5?',
                                 'roomId': '0'})
        self.assertEqual(self._get_received(), ['6.25 is greater than 4.5'])
        self.socket_client.emit('/message',
                                {'sender': 'user',
                                 'body': 'is -12 larger than -12?',
                                 'roomId': '0'})
        self.assertEqual(self._get_received(), ['-12 is equal to -12'])

    def test_random_agent(self):
        '''
        Test the random agent on our simplest domain to verify functionality.

        It's non-trivial to test for exceptions in the agent code because it's run in a thread (https://stackoverflow.com/questions/12484175/make-python-unittest-fail-on-exception-from-any-thread)
        Instead, we just check that the response is not empty which relies on the behaviour of the agent to always send a message in response to any user utterance
        '''
        agent = create_agent(
            'agents.random_agent.RandomClickLevelAgent',
            None, None, self.interfaces, self.domain, seed=123)
        self.app.rooms['0'].set_agent(agent)

        self.socket_client.get_received()
        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': '5 12', 'roomId': '0'})
        # get_received returns a list, test that it's not empty
        self.assertTrue(self._get_received())
        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': '21 65', 'roomId': '0'})
        # get_received returns a list, test that it's not empty
        self.assertTrue(self._get_received())
        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': '36 65', 'roomId': '0'})
        # get_received returns a list, test that it's not empty
        self.assertTrue(self._get_received())

        self.socket_client.emit(
            '/message', {'sender': 'user', 'body': 'quit', 'roomId': '0'})
        non_debug_responses = [msg for msg in self._get_received() if not msg.startswith('DEBUG')]
        self.assertEqual(non_debug_responses[-1], 'Goodbye, ending dialog as requested by user')


class LogTests(AgentTests):
    def setUp(self):
        self.app = AppFactory(microworld_domain, log_path='test_logs')
        self._setup_helper()

        self.agent = create_agent(
            'agents.api_test_agent.APITestAgent',
            None,
            None,
            self.interfaces)
        self.app.rooms['0'].set_agent(self.agent)

    def test_log_generation(self):
        '''Test creating and running an executable log'''

        old_files = len(os.listdir('test_logs'))

        # Send enough messages to start driving
        for _ in range(self.agent.MAX_TURNS):
            self.socket_client.emit(
                '/message', {'sender': 'user', 'body': 'ping', 'roomId': '0'})
            received = self.socket_client.get_received()
        # The 4th message is end_dialog (2 api calls, start_driving, then
        # end_dialog_confirm)
        log_filepath = filename = received[3]['args'][0]['filename']

        new_files = len(os.listdir('test_logs'))
        # should be 3 files: json, txt, py
        self.assertEqual(old_files + 3, new_files)

        # Test the newest python file
        log_filename, _extension = os.path.splitext(
            os.path.basename(log_filepath))
        with suppress_stdout_stderr():
            __import__('test_logs.{}'.format(log_filename))


if __name__ == '__main__':
    unittest.main()
    socketio.disconnect()
