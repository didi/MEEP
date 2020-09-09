import random
import re
from fuzzywuzzy import fuzz

from agents.click_level_agent import ClickLevelAgent, Template, API, WAIT_FOR_USER

end_words = {'goodbye', 'bye', 'stop', 'quit', 'exit', 'thanks', 'thank', 'ty'}


class RandomClickLevelAgent(ClickLevelAgent):
    '''Agent that randomly chooses what to click on'''
    def __init__(self, agent_shared_state, agent_model_path,
                 interfaces, domain, *, seed=None, **kwargs):
        super().__init__(agent_shared_state, agent_model_path, interfaces, domain, **kwargs)
        if seed is not None:
            random.seed(seed)
        self.next_action = None # whether the next action should be wait_for_user
        self.api_tries = 0

    def initial_message(self):
        return {
            'body': 'Hi, I\'m a random agent, but will try to complete the dialog. Type QUIT to force the dialog to end',
            'template': '',
            'variables': [],
            'sender': 'agent',
        }

    def on_message(self, message: str, events: dict) -> dict:
        self.next_action = None
        self.api_tries = 0
        return super().on_message(message, events)

    def predict_action(self, message: str, events: list, available_variables: list):
        next_action = self.next_action
        self.next_action = None

        if next_action is not None:
            return next_action
        elif self.is_end_dialog(message):
            self.next_action = WAIT_FOR_USER
            return self.end_dialog
        elif random.random() < 0.5:
            return random.choice(self.templates)
        else:
            return random.choice(self.api_functions)

    def choose_variable(self, variable_container, available_variables):
        return random.choice(available_variables)

    def fill_template(self, message: str, events: list, template: Template, slot_index: int, available_variables: list, selected_variables: list) -> dict:
        return self.choose_variable(template, available_variables)

    def fill_api(self, message: str, events: list, api: API, slot_index: int, available_variables: list, selected_variables: list) -> dict:
        return self.choose_variable(api, available_variables)

    def is_end_dialog(self, message: str):
        '''Simple rule-based check to see if a message ends the dialog'''
        return any(word in end_words for word in message.lower().split())

    def on_api_call(self, api, selected_variables, debug_message, new_variables):
        # if api call is unsuccessful, try the same API to avoid biasing it to calls
        # that are easier to fill. but if we try too many times, give up
        if new_variables is None:
            self.api_tries += 1
            if self.api_tries < 3:
                self.next_action = api
                self.api_tries += 1
            # else: give up

    def on_template_fill(self, template, selected_variables, message):
        # Reset api tries on a successful template fill
        self.api_tries = 0
        self.next_action = WAIT_FOR_USER

    def on_end_dialog(self, messages, available_variables):
        messages.append({
            'body': 'Goodbye, ending dialog as requested by user',
            'template': 'Goodbye',
            'variables': [],
            'sender': 'agent',
        })

def choices(population, weights=None, *, cum_weights=None, k=1):
    '''
    Polyfill for python <=3.5. Taken from python source on github

    Return a k sized list of population elements chosen with replacement.
        If the relative weights or cumulative weights are not specified,
        the selections are made with equal probability.
    '''
    from math import floor
    from itertools import repeat, accumulate
    from bisect import bisect


    n = len(population)
    if cum_weights is None:
        if weights is None:
            n += 0.0    # convert to float for a small speed improvement
            return [population[floor(random.random() * n)] for i in repeat(None, k)]
        cum_weights = list(accumulate(weights))
    elif weights is not None:
        raise TypeError('Cannot specify both weights and cumulative weights')
    if len(cum_weights) != n:
        raise ValueError('The number of weights does not match the population')
    total = cum_weights[-1] + 0.0   # convert to float
    if total <= 0.0:
        raise ValueError('Total of weights must be greater than zero')
    hi = n - 1
    return [population[bisect(cum_weights, random.random() * total, 0, hi)]
            for i in repeat(None, k)]

if not getattr(random, 'choices', False):
    random.choices = choices

class TypedRandomAgent(RandomClickLevelAgent):
    '''Agent that randomly chooses what to click on, weighted by text overlap'''

    def initial_message(self):
        return {
            'body': 'Hi, I\'m a typed random agent, but will try to complete the dialog. Type QUIT to force the dialog to end',
            'template': '',
            'variables': [],
            'sender': 'agent',
        }

    def fill_template(self, message: str, events: list, template: Template, slot_index: int, available_variables: list, selected_variables: list) -> dict:
        return self.choose_variable(template.slot_descriptions, available_variables, slot_index)

    def fill_api(self, message: str, events: list, api: API, slot_index: int, available_variables: list, selected_variables: list) -> dict:
        return self.choose_variable(api.param_names, available_variables, slot_index)

    def choose_variable(self, slot_descriptions: list, available_variables: list, slot_index: int) -> list:
        # return a list of selected variables
        # rank by name for api call results, rank by value

        MIN_SCORE = 50 # minimum fuzz score to consider strings a match. Arbitrarily chosen
        scores = [fuzz.partial_ratio(slot_descriptions[slot_index], str(var['name'])) for var in available_variables]

        if any(score > 50 for score in scores):
            scores, matching_variables = zip(*[(score, var) for (score, var) in zip(scores, available_variables) if score > 50])
            scores = [score - 40 for score in scores] # subtract 40 from the scores to create a bigger difference. todo: tune this
            selected = random.choices(matching_variables, weights=scores, k=1)[0]
        else:
            selected = random.choice(available_variables)
        return selected