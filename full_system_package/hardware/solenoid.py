import logging

import RPi.GPIO as GPIO

_log = logging.getLogger(__name__)


class Solenoid:
    def __init__(self, pin: int = 18):
        self.pin = pin
        GPIO.setup(self.pin, GPIO.OUT)
        self.close()

    def open(self) -> None:
        _log.info("Solenoid pin %d ON", self.pin)
        GPIO.output(self.pin, GPIO.HIGH)

    def close(self) -> None:
        _log.info("Solenoid pin %d OFF", self.pin)
        GPIO.output(self.pin, GPIO.LOW)

    @property
    def is_active(self) -> bool:
        return GPIO.input(self.pin) == GPIO.HIGH
