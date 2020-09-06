'''
Generate a tsv for human-annotation with columns:
  log_filename starting_address first_user_utterance

This file needs to be human annotated and then manually converted
into a tsv with the following columns [don't output a header]:
    starting_address first_user_utterance destination_description
This converted TSV can be used as the --evaluation_file flag for
gui/backend/main.py
'''
import os
import json


def generate_tsv_to_annotate(log_directory):
    json_logs = [os.path.join(log_directory, f) for f in os.listdir(log_directory)
                 if os.path.isfile(os.path.join(log_directory, f)) and f.endswith(".json")]
    output = []
    for log_file in json_logs:
        with open(log_file, "r") as f:
            log_obj = json.load(f)
        initial_variables = log_obj["initial_variables"]
        source_address = initial_variables["variables"][0][
            "value"] if "variables" in initial_variables else initial_variables[0]["value"]
        if not log_obj.get("events", None):
            print("WARNING: Skipping", log_file, "---ZERO EVENTS")
            continue

        first_event = log_obj["events"][0]
        if first_event.get("event_type", None) != "user_utterance":
            print(
                "WARNING: Skipping",
                log_file,
                "---FIRST EVENT NOT A USER UTTERANCE")
            continue

        first_user_utterance = first_event["utterance"]
        output.append((log_file, source_address, first_user_utterance))
    return output


if __name__ == "__main__":
    rows = generate_tsv_to_annotate(
        "/home/shared/speech_based_destination_chat/dataset/json/dev/")
    print("Generated", len(rows), "dialogs to annotate")
    OUTPUT_TSV = "../gui/backend/evaluation/dev_set.to_annotate.tsv"
    with open(OUTPUT_TSV, "w") as f:
        for r in rows:
            f.write("\t".join(r) + "\n")
    print("Wrote output to ", OUTPUT_TSV)
