class DialogStateNano:
    passenger_actions = {"SAY": 0, "OVER": 1}
    driver_actions = {"DRIVE": 0}
    destination_id = {".": 0, "starbucks": 1, "peets": 2}
    # destination_id = {
    #     "starbucks": 0,
    #     "peets": 1,
    #     "ralphs": 2,
    #     "traderjoes": 3,
    #     "wholefoods": 4,
    #     "walmart": 5,
    #     "cvs": 6,
    #     "toysrus": 7,
    #     "applestore": 8,
    #     "bestbuy": 9
    # }

    def __init__(self, max_actions, desired_destination=None):
        if desired_destination == "":
            self.desired_destination = None
        else:
            self.desired_destination = desired_destination
        self.driven_destination = None
        self.verbal_dialog_history = list()
        self.complete_state = list()
        self.max_actions = max_actions
        self.dialog_complete = False
        self.num_actions = 0
        self.turn = 0

    def update_state(self, action, param):

        complete_action = action + " " + param
        # if action == 'OVER':
        #     self.complete_state.append(action)
        # else:
        self.complete_state.append(complete_action)

        if action == 'SAY':
            self.verbal_dialog_history.append(complete_action)
        elif action == 'DRIVE':  # dialog is complete
            self.dialog_complete = True
            self.driven_destination = param
        elif action == 'OVER':
            # ignore the parameter set with 'OVER'?
            self.turn = (self.turn + 1) % 2

        self.num_actions += 1

    def make_driver_observation(self):
        verbal_dialog_history_ids = [(DialogStateNano.passenger_actions[action.split(" ")[0]],
                                      DialogStateNano.destination_id[action.split(" ")[1]])
                                     for action in self.verbal_dialog_history]
        return {'dialog_history': verbal_dialog_history_ids}

    def make_passenger_observation(self):
        if self.desired_destination:
            destination_id = DialogStateNano.destination_id[self.desired_destination]
        else:
            destination_id = 0
        verbal_dialog_history_ids = [(DialogStateNano.passenger_actions[action.split(" ")[0]],
                                      DialogStateNano.destination_id[action.split(" ")[1]])
                                     for action in self.verbal_dialog_history]
        return {'destination': destination_id,
                'dialog_history': verbal_dialog_history_ids}

    def get_global_state(self):
        return self.desired_destination, self.verbal_dialog_history, self.complete_state, self.driven_destination

    def is_done(self):
        return self.num_actions >= self.max_actions or self.dialog_complete
