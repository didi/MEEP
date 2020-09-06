from rapidfuzz import fuzz

# value is a tuple of params. 0 means query prediciton, 1 means variable
# prediction
API_CALL = {
    'find_place': [0, 1, 1],
    'places_nearby': [0, 1, 1],
    'distance_matrix': [1, 1, 1, 1],
    'start_driving': [1, 1]
}


def fuzzy_string_match(str_ref, str_hyp):
    """Returns fuzzy string similarity score in range [0.0, 1.0]."""

    # The higher the score, the higher the similarity between the two strings.
    return fuzz.ratio(str_ref, str_hyp) / 100.0
