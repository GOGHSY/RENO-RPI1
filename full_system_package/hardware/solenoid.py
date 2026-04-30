import RPi.GPIO as GPIO

class Solenoid:
    def __init__(self, pin=18):
        self.pin = pin
        # Using the setup from your attached code
        GPIO.setup(self.pin, GPIO.OUT)
        self.close() # Default to OFF

    def open(self):
        print(f"Solenoid on pin {self.pin} ON")
        GPIO.output(self.pin, GPIO.HIGH)

    def close(self):
        print(f"Solenoid on pin {self.pin} OFF")
        GPIO.output(self.pin, GPIO.LOW)

    @property
    def is_active(self):
        return GPIO.input(self.pin) == GPIO.HIGH
