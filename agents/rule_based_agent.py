from agents.agent import Agent
import nltk
import googlemaps
import os
from agents.ml.ml_query_extraction import QueryExtractor
from agents.rule_based.keywords import IndicatorType, INDICATORS, PLACES_NEARBY_WORD_TO_INDEX_MAP
import agents.rule_based.utils as utils
import agents.rule_based.params as params
import json
from rapidfuzz import fuzz
import re
import logging


class Destination:
    @staticmethod
    def get_var(api_response, var_name):
        var = None
        for v in api_response:
            if v['name'] == var_name:
                return v['value']
        return var

    @staticmethod
    def get_var_full_name(api_response, var_name):
        var = None
        for v in api_response:
            if v['name'] == var_name:
                return v['full_name']
        return var

    def __init__(self, place_api_response):
        self.name = self.get_var(place_api_response, 'name')
        self.addr = self.get_var(place_api_response, 'address_simple')
        self.st = self.get_var(place_api_response, 'street_name')
        self.lat = self.get_var(place_api_response, 'latitude')
        self.lat_name = self.get_var_full_name(place_api_response, 'latitude')
        self.lng = self.get_var(place_api_response, 'longitude')
        self.lng_name = self.get_var_full_name(place_api_response, 'longitude')
        self.locality = self.get_var(place_api_response, 'locality')
        self.drive_time = self.get_var(place_api_response, 'duration')
        self.drive_distance = self.get_var(place_api_response, 'distance')
        self.rating = self.get_var(place_api_response, 'rating')
        self.open = self.get_var(place_api_response, 'is_open')

        self.location_attribute = "st" if self.st else "addr"


class RuleBasedAgent(Agent):
    '''
    A rule-based agent, a single turn chatbot with canned responses
    '''

    def __init__(self, agent_shared_state,
                 _agent_model_path, interfaces, domain, **kwargs):
        ''' _agent_model_path arg is unused for rule based agent. '''
        super().__init__(agent_shared_state, None, interfaces, domain, **kwargs)
        self.map_api_interface = self.interfaces[0]

        if not 'stop_words' in agent_shared_state:
            print("Initializing Stopwords list...")
            with open(params.STOP_WORD_FILE) as f:
                agent_shared_state['stop_words'] = set(
                    [line.strip('\n').lower() for line in f])
        self.stop_words = agent_shared_state['stop_words']

        if params.ML_QUERY_EXTRACTION_MODEL:
            assert False, "TODO update rule-based agent to support ML query extractor again!"
            print("Initializing ML QueryExtractor...")
            # TODO make the path of the model a parameter
            self.ml_query_extractor = QueryExtractor(
                params.ML_QUERY_EXTRACTION_MODEL)
            print("Done initializing ML QueryExtractor...")
        else:
            self.ml_query_extractor = None
        self.language = "en"

        self.reset_state()

    def reset_state(self):
        self.dst = None
        self.dst_list = None  # from places_nearby
        self.query = ""
        self.relative_landmark_query = None
        self.relative_landmark = None
        # Should be tuple of (API, query, relative_landmark_query)
        self.last_api_signature = (None, None, None)

    def reset(self, initial_variables):
        super().reset(initial_variables)
        self.reset_state()

    def do_start_driving(self):
        self.dst_list = None
        self.query = ""
        self.relative_landmark_query = None
        self.relative_landmark = None
        self.last_api_signature = (None, None, None)

        if self.dst:
            params = [
                {'param': 'dest latitude',
                 'variable_name': self.dst.lat_name,
                 'value': self.dst.lat},
                {'param': 'dest longitude',
                 'variable_name': self.dst.lng_name,
                 'value': self.dst.lng}
            ]
            self.map_api_interface.start_driving(params)
        else:
            self.map_api_interface.start_driving([
                {'param': 'dest latitude', 'variable_name': '', 'value': ''},
                {'param': 'dest longitude', 'variable_name': '', 'value': ''}
            ])

    def extract_query_and_indicators_using_rules(self, message):
        # Remove stop words and find the corresponding user utterance variables
        output_words = []

        dirty_words = [word for word in message.split()]
        cleaned_words = utils.clean_words(dirty_words)

        i = 0
        output_indicators = set([])
        while i < len(cleaned_words):
            indicators = set([])
            cleaned_word = cleaned_words[i]

            for indicator_type in (
                    IndicatorType.CLEAR_CONTEXT, IndicatorType.NO, IndicatorType.PLACES_NEARBY):
                if cleaned_word in INDICATORS[indicator_type]:
                    indicators.add(indicator_type)

            yes_indicator = utils.find_longest_match_indicator(
                cleaned_words[i:], INDICATORS[IndicatorType.YES])
            relative_landmark_indicator = utils.find_longest_match_indicator(
                cleaned_words[i:], INDICATORS[IndicatorType.RELATIVE_LANDMARK])

            if yes_indicator:
                indicators.add(IndicatorType.YES)
                i += len(yes_indicator) - 1
            elif relative_landmark_indicator:
                indicators.add(IndicatorType.RELATIVE_LANDMARK)
                i += len(relative_landmark_indicator) - 1
            elif not indicators:
                dirty_word = dirty_words[i]
                if cleaned_word not in self.stop_words and dirty_word.lower() not in self.stop_words:
                    # Stop words are generated using lowercased dirty words
                    # that are nltk tokenized.
                    for token in nltk.word_tokenize(dirty_word.lower()):
                        token = token.strip()
                        if token not in self.stop_words:
                            output_words.append(token)
                elif (len(dirty_word) > 1 and dirty_word.upper() == dirty_word) or \
                     (i != 0 and len(dirty_word) > 1 and dirty_word[0].upper() == dirty_word[0]
                        and dirty_words[i - 1][-1] != "."):
                    output_words.append(dirty_word)
            i += 1
            output_indicators = output_indicators.union(indicators)

        if not output_words:
            output_indicators.add(IndicatorType.EMPTY_AFTER_FILTERING)
        if IndicatorType.NO in output_indicators:
            output_indicators.add(IndicatorType.CLEAR_CONTEXT)
        if IndicatorType.CLEAR_CONTEXT in output_indicators:
            if IndicatorType.RELATIVE_LANDMARK in output_indicators:
                output_indicators.remove(IndicatorType.RELATIVE_LANDMARK)
            if IndicatorType.YES in output_indicators:
                output_indicators.remove(IndicatorType.YES)
        if len(output_words) >= 2 and IndicatorType.YES in output_indicators:
            output_indicators.remove(IndicatorType.YES)
        logging.debug("query extraction '{}' --> '{}'".format(message,
                                                              ' '.join(output_words)))  # TODO DEBUG
        logging.debug("indicators {}".format(output_indicators))  # TODO DEBUG
        return (' '.join(output_words), output_indicators)

    def extract_target_from_destination_list(self, message, clean_query):
        assert self.dst_list

        if not clean_query:
            return None

        fuzz_scores = []
        for dest in self.dst_list:
            location_description = getattr(
                dest, dest.location_attribute).lower()
            best_score = max([
                fuzz.token_sort_ratio(dest.name.lower(), clean_query),
                fuzz.token_sort_ratio(location_description, clean_query),
                fuzz.token_sort_ratio(dest.name.lower() + " " + location_description, clean_query)])
            fuzz_scores.append((best_score, dest))

        top_fuzz_score, top_dest = sorted(
            fuzz_scores, key=lambda x: (x[0], x[1].name, x[1].drive_time))[-1]

        logging.debug("top_fuzz_score {}".format(top_fuzz_score))
        if top_fuzz_score >= params.MIN_FUZZ_SCORE_FOR_PLACES_NEARBY:
            return top_dest

        for word in message.split():
            cleaned_word = "".join(c for c in word.lower() if c.isalnum())
            index = PLACES_NEARBY_WORD_TO_INDEX_MAP.get(cleaned_word, -1)
            if index >= 0 and index < len(self.dst_list):
                return self.dst_list[index]

        return None

    def append_new_tokens_to_query(self, new_query):
        existing_query_tokens = set(token.lower()
                                    for token in self.query.split())
        new_tokens = [token for token in new_query.split(
        ) if token.lower() not in existing_query_tokens]
        if new_tokens:
            self.query += " " + " ".join(new_tokens)
            return True
        return False

    def ml_query_extraction(self, message, events, api_call):
        if api_call == "places_nearby":
            query = self.ml_query_extractor.extract_places_nearby_query_v2(
                events)
        else:
            query = self.ml_query_extractor.extract_find_place_query_v2(events)

        return query

    def generate_agent_response(self, api_call):
        ''' Generate an agent response utterance by calling find_place or places_nearby.
        '''
        assert api_call in ("places_nearby", "find_place")

        api_signature = (api_call, self.query, self.relative_landmark_query)
        logging.debug("last_api_signature: {}".format(self.last_api_signature))
        logging.debug("new_api_signature: {}".format(api_signature))
        if api_signature == self.last_api_signature:
            return utils.construct_agent_response(
                "Can you be more specific? I couldn't find anything new.", delay=2)

        self.dst_list = None

        src = self.initial_variables
        if self.relative_landmark_query != self.last_api_signature[2]:
            self.relative_landmark = self.extract_relative_landmark(
                self.initial_variables, self.relative_landmark_query)
            logging.debug(
                "Setting new relative landmark {} with query: {}".format(
                    self.relative_landmark,
                    self.relative_landmark_query))
            if self.relative_landmark:
                src = {
                    "latitude": self.relative_landmark.lat,
                    "longitude": self.relative_landmark.lng
                }

        self.last_api_signature = api_signature

        if not self.query:
            return utils.construct_agent_response(
                "Can you be more specific? I couldn't find anything.", delay=2)

        query_params = utils.construct_query_params(src, self.query)

        if api_call == "places_nearby":
            api_response = self.map_api_interface.places_nearby(query_params)[
                'variables']
        else:
            api_response = self.map_api_interface.find_place(query_params)[
                'variables']

        # TODO DEBUG
        # logging.debug("API_RESPONSE %s" % json.dumps(api_response, indent=2))
        # agent_utt = "[query] %s [end] " % (self.query)
        agent_utt = ""

        if len(api_response) == 0:
            agent_utt += "Search yielded zero results. Can you please state clearly, where you want to go? Thanks!"
            self.reset_state()
            return utils.construct_agent_response(agent_utt)

        if api_call == "places_nearby":  # call find_place
            self.dst_list = [Destination(response['value'])
                             for response in api_response]
            if len(self.dst_list) == 1:
                self.dst = self.dst_list[0]
                self.dst_list = None
                agent_utt += "My search only yielded one result. " + \
                             utils.gen_agent_utt_for_single_dst(
                                 self.dst, self.relative_landmark)
            else:
                dest_names = [d.name for d in self.dst_list]
                for i, name in enumerate(dest_names):
                    # if dest_names.count(name) > 1:
                    dest = self.dst_list[i]
                    if dest.st:
                        dest_names[i] = "%s on %s" % (name, dest.st)
                    else:
                        dest_names[i] = "%s located at %s" % (name, dest.addr)

                assert len(self.dst_list) > 1, len(self.dst_list)
                agent_utt += "I found these places: %s. " % (
                    ', '.join("[%d] %s" % (i + 1, name) for i, name in enumerate(dest_names)))
                agent_utt += "They are %s away respectively" % (
                    ', '.join(d.drive_time for d in self.dst_list))
                if self.relative_landmark:
                    agent_utt += " from %s. " % (self.relative_landmark.name)
                else:
                    agent_utt += ". "
                agent_utt += "Is it one of those? "
        else:  # called find_place
            self.dst = Destination(api_response)
            agent_utt += utils.gen_agent_utt_for_single_dst(
                self.dst, self.relative_landmark)
        return utils.construct_agent_response(agent_utt)

    def try_update_query(self, message, query, indicators):
        if IndicatorType.CLEAR_CONTEXT in indicators:
            self.query = query
            self.relative_landmark_query = None
            logging.debug(
                "Updating self.query with CLEAR_CONTEXT --> {}".format(self.query))
        elif IndicatorType.RELATIVE_LANDMARK in indicators and (self.dst or self.dst_list):
            self.relative_landmark_query = query
            logging.debug(
                "Setting new relative landmark query --> {}".format(self.relative_landmark_query))
        else:
            self.append_new_tokens_to_query(query)
            logging.debug(
                "Appended new tokens to self.query --> {}".format(self.query))

    def extract_relative_landmark(self, relative_landmark_query):
        if not relative_landmark_query:
            return None
        query_params = utils.construct_query_params(
            self.initial_variables, relative_landmark_query)
        api_response = self.map_api_interface.find_place(query_params)[
            'variables']
        # logging.debug("relative landmark response:
        # {}".format(json.dumps(api_response, indent=2)))  TODO DEBUG

        if not api_response:
            return None
        else:
            landmark_dst = Destination(api_response)
            if landmark_dst.lat and landmark_dst.lng and landmark_dst.name:
                logging.debug(
                    "Found relative landmark: {}".format(
                        landmark_dst.name))
                return landmark_dst
            else:
                return None

    def try_get_attributes(self, message):
        assert self.dst or self.dst_list
        cleaned_words = set(utils.clean_words(message.split()))

        if set(["what", "whats"]).intersection(cleaned_words) and \
           set(["rating", "ratings"]).intersection(cleaned_words):
            ratings = [
                d.rating for d in self.dst_list] if self.dst_list else [
                self.dst.rating]
            return utils.enumerate_attributes("rating", "ratings", ratings)

        if (set(["where", "wheres"]).intersection(cleaned_words) and "is" in cleaned_words) or \
           (set(["what", "whats"]).intersection(cleaned_words) and
                set(["address", "addresses"]).intersection(cleaned_words)):
            addresses = [
                d.addr for d in self.dst_list] if self.dst_list else [
                self.dst.addr]
            distances = [
                d.drive_distance for d in self.dst_list] if self.dst_list else [
                self.dst.drive_distance]
            return utils.enumerate_attributes("address", "addresses", addresses) + " " + \
                utils.enumerate_attributes(
                "distance", "distances", distances)

        if set(["how", "what", "whats"]).intersection(cleaned_words) and \
           set(["far", "distance", "miles", "km", "kilometers"]).intersection(cleaned_words):
            distances = [
                d.drive_distance for d in self.dst_list] if self.dst_list else [
                self.dst.drive_distance]
            return utils.enumerate_attributes(
                "distance", "distances", distances)

        if set(["what", "which", "whats"]).intersection(cleaned_words) and \
           set(["city", "cities"]).intersection(cleaned_words):
            cities = [
                d.locality for d in self.dst_list] if self.dst_list else [
                self.dst.locality]
            return utils.enumerate_attributes("city", "cities", cities)

        if "open" in cleaned_words:
            if self.dst_list and len(self.dst_list) > 1:
                open_statuses = [d.open for d in self.dst_list]
                if all(status is None for status in open_statuses):
                    return "I'm sorry I do not know if any of these locations are open."
                status_strings = list()
                for status in open_statuses:
                    if status is None:
                        status_strings.append("N/A")
                    elif status:
                        status_strings.append("open")
                    else:
                        status_strings.append("not open")
                prev_vals, last_val = status_strings[:-1], status_strings[-1]
                return "They are %s and %s respectively." % (
                    ", ".join(prev_vals), last_val)
            else:
                dest = self.dst_list[0] if self.dst_list else self.dst
                if dest.open is None:
                    return "I'm sorry, I don't know if it's open or not."
                elif dest.open:
                    return "It is open."
                else:
                    return "It is not open."
        return None

    def on_message(self, message, events):
        query, indicators = self.extract_query_and_indicators_using_rules(
            message)
        if IndicatorType.RELATIVE_LANDMARK not in indicators and \
                (self.dst or self.dst_list):
            attribute_response = self.try_get_attributes(message)
            if attribute_response:
                return utils.construct_agent_response(attribute_response)

        if self.dst_list:
            target_dst = self.extract_target_from_destination_list(
                message, query)
            if target_dst:
                self.dst = target_dst
                logging.debug("CASE: start_driving from dst_list")
                self.do_start_driving()
                return

        if IndicatorType.YES in indicators and not IndicatorType.NO in indicators:
            logging.debug("CASE: YES confirmation")
            if self.dst_list:
                return utils.construct_agent_response(
                    "Please clearly specify a destination from the previous options.")
            elif self.dst:
                self.do_start_driving()
                return

        if not set([IndicatorType.NO, IndicatorType.EMPTY_AFTER_FILTERING]).difference(indicators) and \
                not IndicatorType.PLACES_NEARBY in indicators:
            logging.debug("CASE: Hard no confirmation")
            self.reset_state()
            return utils.construct_agent_response(
                "I am sorry. Can you please state clearly, where you want to go? Thanks!", delay=2)

        self.try_update_query(message, query, indicators)

        if not self.dst and not self.dst_list:
            logging.debug("CASE: Initial")
            api_call = "places_nearby" if IndicatorType.PLACES_NEARBY in indicators else "find_place"
            return self.generate_agent_response(api_call)

        # Refine find_place or places_nearby query
        logging.debug("CASE: Refine query")
        api_call = "places_nearby" if set([IndicatorType.NO, IndicatorType.PLACES_NEARBY]).intersection(indicators) \
                   else "find_place"
        return self.generate_agent_response(api_call)
