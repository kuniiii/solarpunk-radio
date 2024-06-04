import websocket
import uuid
import json
import urllib.request
import urllib.parse
import os
import logging
import random
import tkinter as tk
from tkinter import PhotoImage, Label
from PIL import Image, ImageTk
import io
import time
import threading
from serial_module import SerialReader
import sys

# Initialize the SerialReader
serial_reader = SerialReader('/dev/ttyACM0', 9600)
serial_reader.start()

def setup_logging():
    # Create or get the logger for the 'websocket' library
    logger = logging.getLogger('websocket')
    logger.setLevel(logging.DEBUG)  # Set the desired logging level

    # Create a file handler to write logs to a file
    fh = logging.FileHandler('websocket_trace_again.log')
    fh.setLevel(logging.DEBUG)  # Set the desired level for the file handler

    # Create a formatter and set it for the file handler
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)

    # Add the file handler to the logger
    logger.addHandler(fh)

    # Prevent the 'websocket' logs from propagating to the root logger
    logger.propagate = False

    # Enable WebSocket trace, specifying the logger to use
    websocket.enableTrace(True, handler=fh)

server_address = "artnet.itu.dk:8100"
client_id = str(uuid.uuid4())

# Function to create and return a Tkinter window and label for image display
def create_image_window():
    window = tk.Tk()
    window.title("Received Image")
    # Check if the script was started with --fullscreen argument
    if '--fullscreen' in sys.argv:
        window.attributes('-fullscreen', True)  # Set the window to fullscreen
        window.configure(background='black')  # Set background to black
    else:
        window.configure(background='black')  # Set background to black even if not fullscreen

    # Initial dummy image to initialize the label
    img = PhotoImage(width=1, height=1)
    label = Label(window, image=img, bg='black')  # Ensure label background is also black
    label.image = img  # Keep a reference so it's not garbage collected
    label.pack(expand=True)  # Center the content in the window
    return window, label

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req =  urllib.request.Request("http://{}/prompt".format(server_address), data=data)
    return json.loads(urllib.request.urlopen(req).read())

def blend_images(image1, image2, window, label, steps=10, duration=0.0001):
    """
    Create a smooth transition between two images.
    
    :param image1: The first PIL Image object.
    :param image2: The second PIL Image object.
    :param window: The Tkinter window object.
    :param label: The Tkinter label used for displaying the image.
    :param steps: Number of steps in the transition.
    :param duration: Total duration of the transition in seconds.
    """
    for step in range(steps + 1):
        alpha = step / steps
        blended_image = Image.blend(image1, image2, alpha)
        photo = ImageTk.PhotoImage(blended_image)
        label.config(image=photo)
        label.image = photo  # Keep a reference
        window.update()

execution_complete = True 

def get_images(ws, prompt, window, label):
    global execution_complete
    if not execution_complete:
        print("Execution haven't finished. Ignoring key press.")
        return
    execution_complete = False # Resetting the flag
    prompt_id = queue_prompt(prompt)['prompt_id']
    target_width, target_height = 1392, 768
    previous_image = None

    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            print(message)
            # Check if execution is complete
            if message['type'] == 'executing' and message['data'].get('node') is None:
                execution_complete = True  # Set flag to true when execution is complete
                break  # Exit the loop since execution is done
        else:
            try:
                # Process the image data
                current_image = Image.open(io.BytesIO(out[8:]))  # Load image data from bytes
                # Resize the image to fit the window, maintaining the aspect ratio
                current_image = current_image.resize((target_width, target_height), Image.LANCZOS)

                if previous_image is not None:
                    # Perform the crossfade transition between the previous and current images
                    blend_images(previous_image, current_image, window, label, steps=10, duration=0.00001)
                    # continue
                else:
                    # Directly show the current image if there is no previous image
                    photo = ImageTk.PhotoImage(current_image)
                    label.config(image=photo)
                    label.image = photo  # Keep a reference so it's not garbage collected
                    window.update()

                previous_image = current_image  # Update the previous image
            except Exception as e:
                logging.error(f"Error processing binary message: {e}")

workflow_path = os.path.join(os.path.dirname(__file__), 'workflow_api-sdxl-solarpunk.json')
# workflow_path = os.path.join(os.path.dirname(__file__), 'workflow_api_ws_solarpunk_sdxlturbo.json')
with open(workflow_path, 'r') as file:
    prompt_text = file.read()

prompt = json.loads(prompt_text)

# Setup logging (uncomment if logging is desired)
# setup_logging()

# Initialize Tkinter window and label for image display
window, label = create_image_window()

# Initialize the WebSocket connection
ws = websocket.WebSocket()
ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))

def update_images_based_on_city_change():
    global prompt_text
    current_city = None  # Track the current city to detect changes

    # Define the ranges and corresponding cities
    city_ranges = [
        (208, 250, "Malmo"),
        (251, 290, "Ostrowa"),
        (291, 318, "Danmark"),
        (319, 355, "Luxembourg"),
        (356, 375, "Helsingborg"),  # Adjusted start to 356 to avoid overlap with Luxembourg
        (376, 404, "Lille"),
        (405, 437, "Prague"),
        (438, 461, "Strasbourg"),
        (462, 496, "Light Pro"),
        (497, 540, "Strasbourg I."),
        (541, 568, "Bratislava"),
        (569, 594, "Home Service"),
        (595, 622, "Hilversum II"),
        (623, 668, "Brussel II"),
        (669, 699, "Milano"),
        (700, 722, "Bucharest"),
        (723, 729, "Rom II"),
        (730, 740, "Nancy"),
        (741, 750, "Home Service"),  # Note: "Home Service" is repeated; consider renaming for clarity
        (751, 789, "Sottens"),
        (790, 810, "Hilversum I"),
        (811, 918, "Third Program"),
        (919, 940, "Bruxelles"),
        (941, 954, "Berlin III"),
        (955, 970, "Lyon I"),
        (971, 1000, "Wien II"),
        (1001, 1019, "Stuttgart")
    ]

    while True:
        smoothed_values = serial_reader.get_latest_smoothed_values()
        if smoothed_values:
            last_value = smoothed_values[-1]
            new_city = None

            # Determine the new city based on the last value
            for start, end, city in city_ranges:
                if start <= last_value <= end:
                    new_city = city
                    break  # Exit loop once the correct range is found

            # Check if the city has changed (ignore if new_city is None which means value is out of range)
            if new_city and new_city != current_city:
                current_city = new_city  # Update the current city
                
                # Update the prompt with the new city
                # prompt_text = f"sustainable future {current_city} in the style of Syd Mead."
                prompt_text = f"futuristic sustainable future {current_city}, solarpunk streetscape parks waterfront golden hour colorful in the style of Gropius, Robert McCall, Syd Mead and George Birrell"
                prompt["6"]["inputs"]["text"] = prompt_text
                prompt["3"]["inputs"]["seed"] = random.randint(10**9, 10**10)
                prompt["3"]["inputs"]["steps"] = 10

                print(f"Getting images for: {prompt_text} with seed {prompt['3']['inputs']['seed']}")

                # Call the image generation function
                get_images(ws, prompt, window, label)

        time.sleep(1)  # Wait a bit before checking again to reduce load

# Replace or modify the existing thread start with this updated function call
thread = threading.Thread(target=update_images_based_on_city_change)
thread.daemon = True
thread.start()


# Start the Tkinter event loop
window.mainloop()

# Make sure to close WebSocket connection when the program exits
ws.close()