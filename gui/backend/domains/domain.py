'''
# Base class for creating a new configuration for a domain
# They should be put in the domain directory. New domains that follow the same file pattern as the others
# e.g. (weather_domain `weather/config.py`) can be automatically loaded by main.py with --domain=your-domain
# Otherwise you will need to specify a full class path, e.g. weather.config.weather_domain
'''

import json
from collections import OrderedDict
import os
import sys
sys.path.append(os.path.dirname(__file__))

from utils.utils import add_full_names


class Domain():
    '''Config information needed for a new domain '''

    '''
    EXPERIMENTAL -- optional 'user_templates' arg in constructor below

    When set, constrains users to speak using only templates instead of free text, similar to agent templates.
    This can be useful for producing simpler dialogs to train on, or for implementing simulated users.
    A user template web interface can be accessed by adding the suffix 'template_user' to a Room URL,
    e.g.'http://localhost:8080/0/template_user'.

    User templates for a domain are specified in the same way as agent templates:
    Create a file called 'user_templates.txt' in the domain directory.  The format is the
    same as what is used for agent templates.

    When --domain='destination', the template user interface should be used with the
    '--generate_destinations' flag in gui/backend/main.py so that the user can fill the templates
    with variables for their intended destination.

    For an example of user_template usage in Domain() see gui/backend/domains/destination/config.py.

    Note that this functionality is still experimental and not fully supported.
    '''
    def __init__(self, name: str, interfaces: list, initialization_file: str, apis_file: str,
                 agent_templates: str, user_templates=None):
        self.name = name
        self.interfaces = interfaces

        # Python 3.5 doesn't support open(<PosixPath>)
        # Once we drop support for that, we can use the paths directly
        self.initialization_file = str(initialization_file)
        self.agent_templates = str(agent_templates)
        self.user_templates = None and str(user_templates)
        self.apis_file = str(apis_file)

        self.api_functions, self.end_dialog = self.load_apis(self.apis_file, self.interfaces)
        self.agent_templates_grouped, self.agent_templates_list = self.load_templates(self.agent_templates)
        if user_templates is not None:
            self.user_templates_grouped, self.user_templates_list = self.load_templates(self.user_templates)
        self.initialization = self.load_initialization(self.initialization_file)
        self.initial_variables = self.initialization['initial_variables']
        self.initial_message = self.initialization['initial_message']

    def clone(self, new_interfaces):
        ''' Clone this domain but with new interfaces.  You need separate interfaces for each room beacuse each one has its own manager'''
        return Domain(self.name + '_clone', new_interfaces, self.initialization_file, self.apis_file,
                      self.agent_templates, self.user_templates)

    def load_apis(self, apis_file, interfaces):
        # get active api functions.
        # `api_functions` looks like the list of objects in apis.json except that each
        #  api also has the key 'function' containing the executable function
        # `end_dialog` is a single instance of that^.
        with open(apis_file) as f:
            # api_functions is similar to a list of dict with keys name,
            # endpoint, params, function
            api_functions = {api['endpoint']: api for api in json.load(f)}

        end_dialog = None
        for interface in interfaces:
            for attr in dir(interface):
                function = getattr(interface, attr)

                if hasattr(function, 'endpoint') and function.endpoint in api_functions:
                    if hasattr(function, 'completes_dialog'):
                        assert end_dialog is None, "Found more than one api which ends the dialog"
                        end_dialog = api_functions[function.endpoint]
                        end_dialog['function'] = function
                        del api_functions[function.endpoint]
                    else:
                        api_functions[function.endpoint]['function'] = function
        if end_dialog is None:
            raise Exception('Could not find an API to end dialog')

        # filter out functions not in apis.json
        api_functions = OrderedDict(
            {k: v for k, v in api_functions.items() if 'function' in v})

        return api_functions, end_dialog

    def load_initialization(self, initialization_file):
        with open(initialization_file) as f:
            initialization = json.load(f)

        # Augment every object with full_names
        add_full_names(initialization['initial_variables']['variables'], initialization['initial_variables']['variable_group'])
        return initialization

    def load_templates(self, template_file):
        templates_grouped = OrderedDict()
        templates_list = []
        if template_file is not None:
            with open(template_file) as f:
                current_group = None
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("---") or line.startswith("****"):
                        current_group = line
                    else:
                        if current_group not in templates_grouped:
                            templates_grouped[current_group] = []
                        templates_grouped[current_group].append(line)
                        templates_list.append(line)
        return templates_grouped, templates_list


def load_domain(domain_name: str) -> Domain:
    # Explicitly import known domains. If you want, add yours here to make
    # static analysis work
    if domain_name == 'destination':
        from destination.config import destination_domain
        domain = destination_domain
    elif domain_name == 'weather':
        from weather.config import weather_domain
        domain = weather_domain
    elif domain_name == 'compare_numbers':
        from compare_numbers.config import compare_numbers_domain
        domain = compare_numbers_domain
    elif domain_name == 'microworld' or domain_name == 'microworld2':
        # Microworld should default to the most recent version so that new users prefer it
        from microworld.config import microworld_domain2
        domain = microworld_domain2
    elif domain_name == 'microworld1':
        from microworld.config import microworld1_domain
        domain = microworld_domain

    # If domain contains periods, assume it's a fully qualified name (e.g.
    # destination.config.destination_domain)
    elif '.' in domain_name:
        module_name, _, variable_name = domain_name.rpartition('.')
        module = __import__(module_name, fromlist=variable_name)
        domain = getattr(module, variable_name)

    # Otherwise try a dynamic import so that new domains work without changes to this script
    # Assume that the directory structure is the same as above
    else:
        try:
            domain_module = __import__(
                '{}.config'.format(domain_name), fromlist=[
                    '{}_domain'.format(domain_name)])
            domain = getattr(domain_module, '{}_domain'.format(domain_name))
        except ImportError as e:
            print(
                'Expected to find a variable called {}_domain in {}/{}.py'.format(
                    domain_name,
                    domain_name,
                    domain_name))
            print(e)
            raise

    return domain
