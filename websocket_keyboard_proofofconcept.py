import websocket
import uuid
import json
import urllib.request
import urllib.parse
import os
import logging
import struct
import random
import time
import tkinter as tk
from tkinter import PhotoImage, Label
from PIL import Image, ImageTk
import io
import requests

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
    # Initial dummy image to initialize the label
    img = PhotoImage(width=1, height=1)
    label = Label(window, image=img)
    label.image = img  # Keep a reference so it's not garbage collected
    label.pack()
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
                current_image = current_image.resize((target_width, target_height), Image.ANTIALIAS)

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
with open(workflow_path, 'r') as file:
    prompt_text = file.read()

prompt = json.loads(prompt_text)

# Setup logging (uncomment if logging is desired)
setup_logging()

# Initialize Tkinter window and label for image display
window, label = create_image_window()

# Initialize the WebSocket connection
ws = websocket.WebSocket()
ws.connect("ws://{}/ws?clientId={}".format(server_address, client_id))

# Function to handle key press events
def on_key_press(event):
    global execution_complete
    if execution_complete:
        # Only process the keypress if the previous has been completed
        process_key_press
        window.after(100, lambda: process_key_press(event))
    else:
        print("Execution in progress. Ignoring key press.")
    # Delay processing the new key press to give time for the interrupt to be processed

def process_key_press(event):
    city = None
    if event.char == 's':  # Stockholm
        city = "Stockholm"
    elif event.char == 'o':  # Oslo
        city = "Oslo"
    elif event.char == 'c':  # Copenhagen
        city = "Copenhagen"
    elif event.char == 'b':  # Budapest
        city = "Budapest"
    elif event.char == 'h':  # Helsinki
        city = "Helsinki"

    if city:
        prompt_text = f"sustainable future {city} in the style of Syd Mead"
        prompt["6"]["inputs"]["text"] = prompt_text
        prompt["3"]["inputs"]["seed"] = random.randint(10**9, 10**10)
        prompt["3"]["inputs"]["steps"] = 10
        print(f"Getting images for: {prompt_text} with seed {prompt['3']['inputs']['seed']}")
        get_images(ws, prompt, window, label)

# Bind key press events to the window
window.bind('<KeyPress>', on_key_press)

# Start the Tkinter event loop
window.mainloop()

# Make sure to close WebSocket connection when the program exits
ws.close()