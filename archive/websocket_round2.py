#This is an example that uses the websockets api to know when a prompt execution is done
#Once the prompt execution is done it downloads the images using the /history endpoint

import websocket #NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
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

# def get_images(ws, prompt):
#     prompt_id = queue_prompt(prompt)['prompt_id']
#     output_images = {}
#     image_counter = 0
#     while True:
#         out = ws.recv()
#         if isinstance(out, str):
#             message = json.loads(out)
#             if message['type'] == 'executing':
#                 data = message['data']
#                 if data['node'] is None and data['prompt_id'] == prompt_id:
#                     break # Execution is done
#         else:
#             # Assume binary data contains an image
#             try:
#                 # Check for PNG header based on your documentation
#                 int1, int2 = struct.unpack('>II', out[:8])
#                 if int1 == 1 and int2 == 2:
#                     # It's a PNG image
#                     image_format = 'png'
#                     header_info = f"PNG header detected: {binascii.hexlify(out[:8]).decode()}"
#                 else:
#                     # If not matching PNG header, assume it's a JPEG (or add more checks if needed)
#                     image_format = 'jpg'
#                     header_info = "JPEG data received (header not checked)"
                
#                 logging.debug(f"Image {image_counter}: {header_info}")

#                 image_filename = f'received_image_{image_counter}.{image_format}'  # Create a unique filename based on format
#                 with open(image_filename, 'wb') as image_file:
#                     if image_format == 'png':
#                         image_file.write(out[8:])  # Write PNG data, skipping the initial 8 bytes
#                     else:
#                         image_file.write(out[8:])  # Write JPEG data, skipping the initial 8 bytes
#                 print(f"Image {image_filename} saved.")
#                 image_counter += 1  # Increment the counter for the next image
#             except Exception as e:
#                 logging.error(f"Error processing binary message: {e}")

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
        # time.sleep(duration / steps)

# Example usage:
# Assuming image1 and image2 are your PIL Image objects

# This function would be called instead of directly updating the label's image.
# blend_images(image1, image2, window, label, steps=10, duration=1.0)

def get_images(ws, prompt, window, label):
    prompt_id = queue_prompt(prompt)['prompt_id']
    image_counter = 0
    target_width, target_height = 1392, 768  # Desired dimensions from the JSON configuration
    previous_image = None  # Initialize the previous image variable

    while True:
        out = ws.recv()
        if isinstance(out, str):
            message = json.loads(out)
            if message['type'] == 'executing':
                data = message['data']
                if data['node'] is None and data['prompt_id'] == prompt_id:
                    break  # Execution is done
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
                image_counter += 1  # Increment the counter for the next image
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

# Loop to call get_images every 2 seconds
# try:
#     while True:
#         prompt["3"]["inputs"]["seed"] = random.randint(10**9, 10**10)
#         prompt["3"]["inputs"]["steps"] = 10
#         print(f"The generated seed for the prompt is: {prompt['3']['inputs']['seed']}")
#         get_images(ws, prompt, window, label)
        
#         time.sleep(2)  # Wait for 2 seconds before the next call
# except KeyboardInterrupt:
#     print("Script interrupted by the user. Exiting.")
#     ws.close()
#     window.destroy()