import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


class TurbiditySensor:
    def __init__(self, pin=0):
        # Initialize I2C and ADS1115
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.ads = ADS.ADS1115(self.i2c)

        # Create analog channel
        self.chan = AnalogIn(self.ads, pin)

    def read_voltage(self):
        """Read voltage from sensor"""
        return self.chan.voltage

    def calculate_ntu(self, voltage):
        """Convert voltage to NTU"""
        ntu = -1120.4 * (voltage ** 2) + 5742.3 * voltage - 4352.9

        # Clamp values
        if ntu < 0:
            ntu = 0
        if voltage > 4.2:
            ntu = 0

        return ntu

    def read(self):
        """Return both voltage and turbidity"""
        voltage = self.read_voltage()
        ntu = self.calculate_ntu(voltage)
        return voltage, ntu

    def print_reading(self):
        """Print formatted output"""
        voltage, ntu = self.read()
        print(f"Voltage: {round(voltage, 3)} V")
        print(f"Estimated Turbidity: {round(ntu, 2)} NTU")
        print("-------------------------")
