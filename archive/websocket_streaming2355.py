import websocket
import uuid
import json
import urllib.request
import urllib.parse
import threading
import signal
from PIL import Image
import io
import os
import logging
import struct


def setup_logging():
    logger = logging.getLogger('websocket')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('websocket_trace.log')
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    websocket.enableTrace(True, handler=fh)

server_address = "0.0.0.0:8100"
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    # print("entering queue prompt")
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

# def get_image(filename, subfolder, folder_type):
#     data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
#     url_values = urllib.parse.urlencode(data)
#     with urllib.request.urlopen(f"http://{server_address}/view?{url_values}") as response:
#         return response.read()

# def get_history(prompt_id):
#     with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}") as response:
#         return json.loads(response.read())

# def display_image(image_data):
#     image = Image.open(io.BytesIO(image_data))
#     image.show()

# def get_images(prompt_id):
#     output_images = {}
#     print(f"Fetching images for Prompt ID: {prompt_id}")

#     history = get_history(prompt_id)
#     if prompt_id in history:
#         for node_id in history[prompt_id]['outputs']:
#             node_output = history[prompt_id]['outputs'][node_id]
#             if 'images' in node_output:
#                 images_output = []
#                 for image in node_output['images']:
#                     image_data = get_image(image['filename'], image['subfolder'], image['type'])
#                     images_output.append(image_data)
#                 output_images[node_id] = images_output

#     for node_id in output_images:
#         for image_data in output_images[node_id]:
#             display_image(image_data)

#     return output_images

def on_message(ws, message):
    # Check if the message is binary data or a string (text message)
    if isinstance(message, bytes):
        try:
            # Handle binary data (assuming it's an image)
            int1, int2 = struct.unpack('>II', message[:8])
            if int1 == 1 and int2 == 2:
                png_data = message[8:]  # Extract the PNG data
                with open('received_image.png', 'wb') as image_file:
                    image_file.write(png_data)
                print("Image saved.")
        except Exception as e:
            print(f"Error processing binary message: {e}")
    elif isinstance(message, str):
        try:
            # Handle text message (assuming it's JSON)
            data = json.loads(message)
            print(f"Received text message: {data}")
            # Add your logic here to handle the text message,
            # such as checking for 'type': 'executed' messages
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from message: {e}")
    else:
        print("Received unknown message type")

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed")

def on_open(ws):
    print("WebSocket connection opened")

def run_websocket():
    setup_logging()
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(f"ws://{server_address}/ws?clientId={client_id}",
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()

def main():
    ws_thread = threading.Thread(target=run_websocket)
    ws_thread.daemon = True  # Daemonize thread to ensure it exits when the main program does
    ws_thread.start()

    # Load prompt from 'workflow.json'
    workflow_path = os.path.join(os.path.dirname(__file__), 'workflow_api-ws-only.json')
    with open(workflow_path, 'r') as file:
        prompt = json.load(file)

    # This queues the prompt. The response is not used directly here but starts the process on the server.
    queue_prompt_response = queue_prompt(prompt)
    print(f"Prompt queued with response: {queue_prompt_response}")

    # Keep the main thread running, otherwise it will exit and kill the daemon threads
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Interrupt received, shutting down...")



if __name__ == "__main__":
    main()
import websocket
import uuid
import json
import urllib.request
import urllib.parse
import threading
import signal
from PIL import Image
import io
import os
import logging
import struct


def setup_logging():
    logger = logging.getLogger('websocket')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('websocket_trace.log')
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    websocket.enableTrace(True, handler=fh)

server_address = "0.0.0.0:8100"
client_id = str(uuid.uuid4())

def queue_prompt(prompt):
    # print("entering queue prompt")
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

def on_message(ws, message):
    global client_id  # Use if necessary for the request
    
    if isinstance(message, str):  # Handle JSON/text messages
        data = json.loads(message)
        print(f"Received text message: {data}")
        
        # Check for 'queue_remaining' status updates
        if data.get('type') == 'status' and data.get('data', {}).get('status', {}).get('exec_info', {}).get('queue_remaining', 0) > 0:
            print("Items in queue, acting on next item.")
            handle_queue_items()

    elif isinstance(message, bytes):  # Binary data handling (for images)
        try:
            # Existing binary data handling logic
            process_binary_image_data(message)
        except Exception as e:
            print(f"Error processing binary message: {e}")
    else:
        print("Received unknown message type")

def handle_queue_items():
    # Example: Re-queue a prompt
    workflow_path = os.path.join(os.path.dirname(__file__), 'workflow_api-ws-only.json')
    with open(workflow_path, 'r') as file:
        prompt = json.load(file)
    
    queue_prompt_response = queue_prompt(prompt)
    print(f"Re-queued prompt with response: {queue_prompt_response}")

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed")

def on_open(ws):
    print("WebSocket connection opened")

def run_websocket():
    setup_logging()
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(f"ws://{server_address}/ws?clientId={client_id}",
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()

def main():
    ws_thread = threading.Thread(target=run_websocket)
    ws_thread.daemon = True  # Daemonize thread to ensure it exits when the main program does
    ws_thread.start()

    # Load prompt from 'workflow.json'
    workflow_path = os.path.join(os.path.dirname(__file__), 'workflow_api-ws-only.json')
    with open(workflow_path, 'r') as file:
        prompt = json.load(file)

    # This queues the prompt. The response is not used directly here but starts the process on the server.
    queue_prompt_response = queue_prompt(prompt)
    print(f"Prompt queued with response: {queue_prompt_response}")

    # Keep the main thread running, otherwise it will exit and kill the daemon threads
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Interrupt received, shutting down...")



if __name__ == "__main__":
    main()
