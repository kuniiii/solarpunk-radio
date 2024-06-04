import serial

SERIAL_PORT = '/dev/ttyACM0'  # Adjust this to your Arduino's port
BAUD_RATE = 9600

class ExponentialSmoothing:
    def __init__(self, alpha=0.01):  # Smoothing factor alpha; adjust as needed
        self.alpha = alpha
        self.smoothed = None
    
    def add_value(self, value):
        if self.smoothed is None:  # For the first value, initialize smoothed value
            self.smoothed = value
        else:
            self.smoothed = self.alpha * value + (1 - self.alpha) * self.smoothed
        return self.smoothed

# Initialize an ExponentialSmoothing filter for each stream of data
smoothing_filters = [ExponentialSmoothing(alpha=0.01) for _ in range(4)]  # Adjust alpha here

def parse_and_smooth(line):
    parts = line.split(';')
    smoothed_values = []
    
    for i, part in enumerate(parts):
        try:
            value = float(part)  # Exponential smoothing works on floating point numbers
            smoothed_value = smoothing_filters[i].add_value(value)
            smoothed_values.append(int(smoothed_value))  # Convert back to int for display, removing decimals
        except ValueError:
            print(f"Error parsing part '{part}' to float.")
    
    return smoothed_values

def main():
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        print(f"Opened {SERIAL_PORT} at {BAUD_RATE} baud. Press CTRL+C to terminate.")
        
        max_line_length = 0

        try:
            while True:
                if ser.in_waiting > 0:
                    line = ser.readline().decode().strip()
                    smoothed_values = parse_and_smooth(line)
                    # Convert smoothed values to string
                    smoothed_values_str = '\t'.join([str(value) for value in smoothed_values])
                    # Only show the smoothed values
                    output_line = f"\rSmoothed: {smoothed_values_str}"
                    # Ensure we clear any previous text by padding with spaces
                    print(f"{output_line}{' ' * (max_line_length - len(output_line))}", end="")
                    max_line_length = max(max_line_length, len(output_line))
        except KeyboardInterrupt:
            print("\nTerminated by user")


if __name__ == "__main__":
    main()
