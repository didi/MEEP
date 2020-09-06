#!/usr/bin/env bash

python eval_click_level.py click_level_hypothesis click_level_gold --all

# you should see the following results:
#
# 05/28/2020 16:59:37: INFO: scores:
#
# category                             acc       hit     total
# ------------------------------------------------------------
# PREDICTION accuracy:                0.70     34.23     49.00
# action prediction accuracy:         0.57     12.00     21.00
# query prediction accuracy:          0.81      3.23      4.00
# variable prediction accuracy:       0.79     19.00     24.00
# joint action prediction accuracy:   0.43      9.00     21.00
# destination accuracy:               0.67      2.00      3.00
#
# 05/28/2020 16:59:37: INFO: (copy/paste string to spreadsheet)
# 0.70    0.57    0.81    0.79    0.43
# 05/28/2020 16:59:37: INFO: scores by log:
#
# log_id           PREDICT_acc     action_acc      query_acc   variable_acc    joint_action_acc
# ---------------------------------------------------------------------------------------------
# log_188.txt             0.61           0.78           0.61           0.44                0.44
# log_165.txt             0.73           0.33           1.00           1.00                0.33
# log_138.txt             0.79           0.50           1.00           1.00                0.50
