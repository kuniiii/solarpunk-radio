import tkinter as tk
from PIL import Image, ImageTk
import threading
import websocket
import io
import json
import urllib.request
import urllib.parse
import time

# Initialize Tkinter window
window = tk.Tk()
window.title('WebSocket Received Images')
image_label = tk.Label(window)
image_label.pack()

server_address = "artnet.itu.dk:8100"
client_id = "d7cfb39d-e7b3-4f71-a5c1-330a59372877"

# Functions: queue_prompt, get_image, get_history, and get_images as provided

def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    return json.loads(urllib.request.urlopen(req).read())

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    print(data)
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{server_address}/view?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{server_address}/history/{prompt_id}") as response:
        return json.loads(response.read())

def get_images(prompt_id):
    output_images = {}
    print(f"Fetching images for Prompt ID: {prompt_id}")

    history = get_history(prompt_id)
    print(history)
    if prompt_id in history:
        for node_id in history[prompt_id]['outputs']:
            node_output = history[prompt_id]['outputs'][node_id]
            if 'images' in node_output:
                images_output = []
                for image in node_output['images']:
                    image_data = get_image(image['filename'], image['subfolder'], image['type'])
                    images_output.append(image_data)
                output_images[node_id] = images_output

    for node_id in output_images:
        for image_data in output_images[node_id]:
            display_image(image_data)

    return output_images

def periodically_fetch_images(prompt_id, interval=5):
    """
    Fetch new images based on the execution history and update the Tkinter window.
    :param prompt_id: The ID of the prompt execution to monitor.
    :param interval: How often to check for new images, in seconds.
    """
    last_displayed_image_index = -1  # No images displayed initially
    while True:
        time.sleep(interval)  # Wait for a given interval
        history = get_history(prompt_id)[prompt_id]
        for o in history['outputs']:
            for node_id in history['outputs']:
                node_output = history['outputs'][node_id]
                if 'images' in node_output:
                    images_output = []
                    for index, image in enumerate(node_output['images']):
                        print("hello")
                        # if index > last_displayed_image_index:
                            # image_data = get_image(image['filename'], image['subfolder'], image['type'])
                            # images_output.append(image_data)
                            # last_displayed_image_index = index
                            # display_image(image_data)  # Display each new image

def display_image(image_data):
    """
    Update the Tkinter window with a new image.
    :param image_data: Binary data of the image to display.
    """
    image = Image.open(io.BytesIO(image_data))
    photo = ImageTk.PhotoImage(image)
    image_label.config(image=photo)
    image_label.image = photo  # Keep a reference!

def start_image_stream(prompt):
    """
    Start the process to monitor prompt execution and fetch images as they become available.
    :param prompt: The prompt configuration.
    """
    prompt_id = queue_prompt(prompt)['prompt_id']
    threading.Thread(target=periodically_fetch_images, args=(prompt_id,), daemon=True).start()

# Example prompt initialization and call to start_image_stream
prompt_text = """
{
  "3": {
    "inputs": {
      "seed": 341505144615130,
      "steps": 20,
      "cfg": 8,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": [
        "4",
        0
      ],
      "positive": [
        "6",
        0
      ],
      "negative": [
        "7",
        0
      ],
      "latent_image": [
        "5",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "4": {
    "inputs": {
      "ckpt_name": "v1-5-pruned-emaonly.ckpt"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "Load Checkpoint"
    }
  },
  "5": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "Empty Latent Image"
    }
  },
  "6": {
    "inputs": {
      "text": "masterpiece best quality girl",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "7": {
    "inputs": {
      "text": "bad hands",
      "clip": [
        "4",
        1
      ]
    },
    "class_type": "CLIPTextEncode",
    "_meta": {
      "title": "CLIP Text Encode (Prompt)"
    }
  },
  "8": {
    "inputs": {
      "samples": [
        "3",
        0
      ],
      "vae": [
        "4",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE Decode"
    }
  },
  "10": {
    "inputs": {
      "images": [
        "8",
        0
      ]
    },
    "class_type": "ETN_SendImageWebSocket",
    "_meta": {
      "title": "Send Image (WebSocket)"
    }
  }
}
"""

prompt = json.loads(prompt_text)
# prompt["6"]["inputs"]["text"] = "masterpiece best quality girl"
# prompt["3"]["inputs"]["seed"] = 5

# Start the image stream in a separate thread
threading.Thread(target=start_image_stream, args=(prompt,), daemon=True).start()

window.mainloop()
