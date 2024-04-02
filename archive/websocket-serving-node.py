import asyncio
import websockets
import base64
import json
import aiofiles

connected = set()  # Moved here for clarity

# Asynchronous function to save base64 encoded images
async def save_base64_image(base64_string, file_path):
    binary_data = base64.b64decode(base64_string)
    async with aiofiles.open(file_path, 'wb') as file:
        await file.write(binary_data)
    print(f'Image saved successfully: {file_path}')

# Handler for each client connection
async def connection_handler(websocket, path):
    print("WebSocket client connected")
    connected.add(websocket)  # Add client to the set of connected clients
    try:
        async for message in websocket:
            try:
                parsed = json.loads(message)
                await save_base64_image(parsed['base64_img'], f"{parsed['_requestId']}_image.webp")
            except Exception as e:
                print("Error occurred when getting a message", e)
    finally:
        connected.remove(websocket)  # Ensure removal even if an error occurs
        print("WebSocket client disconnected")

# Function to send messages to all connected clients
async def send_message(message):
    if connected:  # Check if there are any connected clients
        await asyncio.wait([ws.send(message) for ws in connected if ws.open])
        print("Messaging Everyone a 'hi'")

# Start the WebSocket server
async def start_server():
    async with websockets.serve(connection_handler, "0.0.0.0", 8022):
        print("Listening on 8022")
        while True:
            # Increment and send a message every 5 seconds
            global i
            i += 1
            await send_message(json.dumps({"_requestId": i, "prompt": "Cow"}))
            await asyncio.sleep(5)

i = 0

# Entry point for the async event loop
async def main():
    # Starting the server
    await start_server()

# Running the main function using asyncio
asyncio.run(main())
