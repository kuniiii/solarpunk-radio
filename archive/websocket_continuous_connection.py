# Save this script as example.py and run with Python 3.
import tkinter as tk
from tkinter import Label
from PIL import Image, ImageTk
import io
import websocket
import threading
import uuid
import json
import random
import logging
import struct
import os
import time

def setup_logging():
    logger = logging.getLogger('websocket')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('websocket_debug.log')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    websocket.enableTrace(True, handler=fh)
    logger.propagate = False

def create_image_window():
    window = tk.Tk()
    window.title("Received Image")
    label = Label(window)
    label.pack()
    return window, label

def update_image_on_label(window, label, image_data):
    photo = ImageTk.PhotoImage(image=Image.open(io.BytesIO(image_data)))
    label.configure(image=photo)
    label.image = photo  # Keep a reference.
    window.update()

def on_message(ws, message, args):
    window, label = args
    if not isinstance(message, str):
        int1, int2 = struct.unpack('>II', message[:8])
        if int1 == 1 and int2 == 2:  # It's a PNG image.
            update_image_on_label(window, label, message[8:])
    # Add more message handling logic here if needed.

def send_prompt(ws, prompt):
    """Send a prompt via the WebSocket connection."""
    try:
        if ws.sock and ws.sock.connected:
            ws.send(json.dumps(prompt))
        else:
            print("WebSocket is not connected.")
    except Exception as e:
        print(f"Exception in send_prompt: {e}")

def continuous_send(ws, prompt):
    """Continuously send prompts to the WebSocket server."""
    while True:
        prompt["3"]["inputs"]["seed"] = random.randint(10**9, 10**10)
        print(f"The generated seed for the prompt is: {prompt['3']['inputs']['seed']}")
        send_prompt(ws, prompt)
        time.sleep(2)  # Adjust as necessary

if __name__ == "__main__":
    # Setup logging, window, and label
    setup_logging()
    
    server_address = "0.0.0.0:8100"
    client_id = str(uuid.uuid4())
    ws_url = f"ws://{server_address}/ws?clientId={client_id}"
    
    workflow_path = os.path.join(os.path.dirname(__file__), 'workflow_api_ws_solarpunk_sdxlturbo.json')

    with open(workflow_path, 'r') as file:
        prompt = json.loads(file.read())

    window, label = create_image_window()

    # Initialize WebSocketApp with the corrected on_message callback
    ws = websocket.WebSocketApp(ws_url, on_message=lambda ws, msg: on_message(ws, msg, (window, label)))

    def on_open(ws):
        print("WebSocket connection opened.")
        # Start the prompt sending thread once the connection is open
        send_thread = threading.Thread(target=continuous_send, args=(ws, prompt))
        send_thread.daemon = True
        send_thread.start()

    ws.on_open = on_open

    # Run the WebSocket connection in a separate thread
    ws_thread = threading.Thread(target=ws.run_forever)
    ws_thread.daemon = True
    ws_thread.start()

    window.mainloop()