class DialogStateNano:
    passenger_actions = {
        "wait for driver": 0,
        "say starbucks": 1,
        "say peets": 2,
        "mental starbucks": 3,
        "mental peets": 4}
    driver_actions = {
        "wait for passenger": 0,
        "drive starbucks": 1,
        "drive peets": 2}
    # if not present, then destination is not set -- None
    destination_id = {"starbucks": 1, "peets": 2}

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

    def update_state(self, action):

        self.complete_state.append(action)
        if 'mental' in action:
            self.desired_destination = action.split(" ")[1]
        elif 'say' in action:
            self.verbal_dialog_history.append(action)
        elif action.startswith('drive'):  # dialog is complete
            self.dialog_complete = True
            self.driven_destination = action.split(' ')[1]

        self.num_actions += 1

    def make_driver_observation(self):
        verbal_dialog_history_ids = [
            DialogStateNano.passenger_actions[action] for action in self.verbal_dialog_history]
        return {'dialog_history': verbal_dialog_history_ids}

    def make_passenger_observation(self):
        if self.desired_destination:
            destination_id = DialogStateNano.destination_id[self.desired_destination]
        else:
            destination_id = 0
        verbal_dialog_history_ids = [
            DialogStateNano.passenger_actions[action] for action in self.verbal_dialog_history]
        return {'destination': destination_id,
                'dialog_history': verbal_dialog_history_ids}

    def get_global_state(self):
        return self.desired_destination, self.verbal_dialog_history, self.complete_state, self.driven_destination

    def is_done(self):
        return self.num_actions >= self.max_actions or self.dialog_complete
