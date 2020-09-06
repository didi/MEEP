from enum import Enum


class IndicatorType(Enum):
    CLEAR_CONTEXT = 1
    YES = 2
    NO = 3
    PLACES_NEARBY = 4
    RELATIVE_LANDMARK = 5
    EMPTY_AFTER_FILTERING = 6


INDICATORS = {
    IndicatorType.CLEAR_CONTEXT:
        set(['hm', 'hmm', 'hrm', 'oops', 'sorry', 'actually']),
    IndicatorType.YES: {
        'yes': [[]], 'sure': [[]], 'alright': [[]], 'definitely': [[]],
        'ok': [[]], 'okay': [[]], 'yep': [[]], 'yeah': [[]], 'yah': [[]],
        'perfect': [[]], 'great': [[]],
        'lets': [['roll'], ['go'], ['leave']],
        'sounds': [['good']],
        'thats': [['it'], ['right'], ['the', 'one']],
            },
    IndicatorType.NO:
        set(['not', 'no']),
    IndicatorType.PLACES_NEARBY:
        set([
            'any',
            'anything',
            'anywhere',
            'nearby',
            'nearer',
            'nearest',
            'closer',
            'closest',
            'farther',
            'farthest',
            'further',
            'furthest',
            'another',
            'other',
            'others',
            'places',
            'around',
            'option',
            'options',
            'someplace',
            'suggest',
            'suggestion',
            'suggestions',
            'recommend',
            'recommendation',
            'recommendations',
        ]),
    IndicatorType.RELATIVE_LANDMARK: {
        'across': [['the', 'street']],
        'next': [['to']],
        'near': [[]],
        'by': [[]],
        'close': [['to']],
        'from': [[]],
            },
}
PLACES_NEARBY_WORD_TO_INDEX_MAP = {
    "first": 0,
    "second": 1,
    "third": 2,
    "1st": 0,
    "2nd": 1,
    "3rd": 2
}
