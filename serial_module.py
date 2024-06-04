# serial_module.py

import serial
import threading

SERIAL_PORT = '/dev/ttyACM0'
BAUD_RATE = 9600

class ExponentialSmoothing:
    def __init__(self, alpha=0.01):
        self.alpha = alpha
        self.smoothed = None

    def add_value(self, value):
        if self.smoothed is None:
            self.smoothed = value
        else:
            self.smoothed = self.alpha * value + (1 - self.alpha) * self.smoothed
        return self.smoothed

smoothing_filters = [ExponentialSmoothing(alpha=0.01) for _ in range(4)]

class SerialReader:
    def __init__(self, port, baud_rate):
        self.ser = serial.Serial(port, baud_rate, timeout=1)
        self.thread = None
        self.running = False
        self.latest_values = []

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.read_loop)
        self.thread.start()

    def read_loop(self):
        while self.running:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode().strip()
                self.latest_values = self.parse_and_smooth(line)

    def parse_and_smooth(self, line):
        parts = line.split(';')
        smoothed_values = []
        for i, part in enumerate(parts):
            try:
                value = float(part)
                smoothed_value = smoothing_filters[i].add_value(value)
                smoothed_values.append(int(smoothed_value))
            except ValueError:
                print(f"Error parsing part '{part}' to float.")
        return smoothed_values

    def get_latest_smoothed_values(self):
        return self.latest_values

    def stop(self):
        self.running = False
        self.thread.join()

# If running this script directly, demonstrate its standalone functionality
if __name__ == "__main__":
    sr = SerialReader(SERIAL_PORT, BAUD_RATE)
    try:
        sr.start()
        input("Serial reading... Press Enter to stop.\n")
    finally:
        sr.stop()
