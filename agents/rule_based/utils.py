import logging


def clean_words(words):
    '''
        args:
            words - list of word tokens
        returns:
            list of words lowercased and with non-alphanumeric characters removed.
    '''

    return ["".join(c for c in word.lower() if c.isalnum()) for word in words]

# TODO Write unittest


def find_longest_match_indicator(cleaned_word_tokens, indicator_map):
    '''
    Finds the longest match indicator, STARTING from the first token,
    e.g. if first token doesn't match, no matches will be returned.

    args:
        cleaned_word_tokens - list that is lowercased with all all non-alphanumeric characters removed.

    returns:
        The longest match in the form of a list of word tokens.
        If no match was found, returns None
    '''
    first_word = cleaned_word_tokens[0]
    other_words = cleaned_word_tokens[1:] if len(
        cleaned_word_tokens) > 1 else []

    longest_matching_suffix = None
    if first_word in indicator_map:
        suffixes = indicator_map[first_word]
        assert suffixes
        for suffix in suffixes:
            if len(other_words) < len(suffix):
                continue
            if longest_matching_suffix is None or len(
                    suffix) > len(longest_matching_suffix):
                clean_suffix = other_words[:len(suffix)]
                if clean_suffix == suffix:
                    longest_matching_suffix = suffix

    output = None if longest_matching_suffix is None else [
        first_word] + longest_matching_suffix
    if output:
        logging.debug("Found indicator: {}".format(output))
    return output


def gen_agent_utt_for_single_dst(dst, relative_landmark=None):
    agent_utt = ""
    if dst.drive_time is None or dst.drive_distance is None:
        agent_utt += "Do you mean {}? ".format(dst.name)
    else:
        if dst.st:
            if dst.locality:
                agent_utt += "I found {} on {} in {}. ".format(
                    dst.name, dst.st, dst.locality)
            else:
                agent_utt += "I found {} on {}. ".format(dst.name, dst.st)
#            elif dst.locality:
#                agent_utt += "There is a {} in {}. ".format(dst.name, dst.locality)
        elif dst.addr:
            agent_utt += "Do you mean {}? The address is {}. ".format(
                dst.name, dst.addr)
        elif dst.locality:
            agent_utt += "I found {} on {}. ".format(dst.name, dst.locality)
        else:
            agent_utt += "I found {}. I could not find its address though. ".format(
                dst.name)

        if dst.drive_time is not None and dst.drive_distance is not None:
            if relative_landmark:
                agent_utt += "It is {} and {} away from {}. Shall we go?"\
                             .format(dst.drive_time, dst.drive_distance, relative_landmark.name)
            else:
                agent_utt += "It is {} and {} away. Shall we go?".format(
                    dst.drive_time, dst.drive_distance)
        elif dst.drive_time:
            if relative_landmark:
                agent_utt += "It is {} away from {}. Shall we go?".format(
                    dst.drive_time, relative_landmark.name)
            else:
                agent_utt += "It is {} away. Shall we go?".format(
                    dst.drive_time)
        elif dst.drive_distance:
            if relative_landmark:
                agent_utt += "It is {} away from {}. Shall we go?".format(
                    dst.drive_distance, relative_landmark.name)
            else:
                agent_utt += "It is {} away. Shall we go?".format(
                    dst.drive_distance)
        else:
            agent_utt += "Shall we go?"
    return agent_utt


def construct_agent_response(agent_utterance, delay=None):
    out = {
        'body': agent_utterance,
        'template': agent_utterance,
        'variables': []
    }
    if delay:
        out['delay'] = delay
    return out


def enumerate_attributes(attr_name_singular, attr_name_plural, attr_values):
    assert attr_values
    if len(attr_values) == 1:
        if attr_values[0] is not None:
            return "Its %s is %s." % (attr_name_singular, str(attr_values[0]))
        else:
            return "I'm sorry there is no %s available." % attr_name_singular
    if all(val is None for val in attr_values):
        return "I'm sorry %s are not available for any of the places." % (
            attr_name_plural)
    values = [str(val) if val is not None else "N/A" for val in attr_values]
    prev_vals, last_val = values[:-1], values[-1]
    return "Their %s are %s and %s respectively." % (
        attr_name_plural, ", ".join(prev_vals), last_val)


def construct_query_params(source, query):
    ''' for find_place and places_nearby APIs '''
    return [
        {'param': 'query', 'variable_name': '"%s"' % query, 'value': query},
        {'param': 'src latitude',
         'variable_name': 'source_latitude',
         'value': source['latitude']},
        {'param': 'src longitude',
         'variable_name': 'source_longitude',
         'value': source['longitude']}
    ]
