import shared_state


class ControlManager:
    def __init__(self):
        self.v1_state = "OPEN"
        self.v2_state = "CLOSED"

    def should_shutdown(self, turbidity):
        if turbidity > shared_state.get_threshold():
            self.v1_state = "CLOSED"
            self.v2_state = "OPEN"
            return True
        else:
            self.v1_state = "OPEN"
            self.v2_state = "CLOSED"
            return False
