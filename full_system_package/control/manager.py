class ControlManager:
    def __init__(self):
        self.v1_state = "OPEN"
        self.v2_state = "CLOSED"
        self.turbidity_threshold = 10  # adjust as needed

    def should_shutdown(self, turbidity):
        if turbidity > self.turbidity_threshold:
            self.v1_state = "CLOSED"
            self.v2_state = "OPEN"
            return True
        else:
            self.v1_state = "OPEN"
            self.v2_state = "CLOSED"
            return False
