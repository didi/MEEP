"""
Script for converting raw click logs to readable dialogs
Very specific to the current log formatting
"""

import ast
import sys
import os

log_fname = sys.argv[1]
log_fin = open(log_fname)

root, ext = os.path.splitext(log_fname)
log_fout = open(root + "_dialogs" + ext, "w+")

n = 0

for line in log_fin.readlines():
    message = " ".join(line.strip().split()[2:])
    if message == "Resetting environment":
        n += 1
        # start recording dialog
        log_fout.write("==== EPISODE {} ====\n".format(n))
    elif message.startswith("Received end dialog message:"):
        output = ast.literal_eval(
            message[len("Received end dialog message:") + 1:])
        log_fout.write("Correct result? {}\n".format(output["correct"]))
    else:
        for agent in "Passenger", "Driver":
            prefix = "--- {} completed an action:".format(agent)
            if message.startswith(prefix):
                command = ast.literal_eval(message[len(prefix) + 1:])
                if "{}" in command[0]:
                    utterance = command[0].format(command[1]["value"])
                    log_fout.write("{}: {}\n".format(agent.upper(), utterance))
                else:
                    args = ", ".join(
                        ["{}={}".format(arg["full_name"], arg["value"]) for arg in command[1:]])
                    log_fout.write(
                        "API_CALL: {}\n".format(
                            "{}({})".format(
                                command[0], args)))

log_fin.close()
log_fout.close()
