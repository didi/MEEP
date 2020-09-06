# TODO Instead of hard-coding these params, make them config files that are passed
#      as arguments to Agent initialization.

STOP_WORD_FILE = "static/stop_words.txt"
#ML_QUERY_EXTRACTION_MODEL = "/home/scotfang/gits/dest-handwritten/ml-param-extraction/training_runs/20200107/max_seq_length512/"
# When set to None, use stopwords and perform rule-based query extraction
ML_QUERY_EXTRACTION_MODEL = None
# If using the ML model for query extraction, persist ML query contexts
# using rules
MULTI_TURN_ML_QUERIES = True
MIN_FUZZ_SCORE_FOR_PLACES_NEARBY = 75  # Set this in range [0,100]
