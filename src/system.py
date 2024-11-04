"""
The system is the place to define system logic, automation, services, etc. as a whole.  It should
provide an *Initialize* method that will be called in main to start the start the system after
variables, devices, and UIs have been defined.

Examples of items in the system file:
* Clocks and scheduled things
* Connection of devices that need connecting
* Set up of services (e.g. ethernet servers, CLIs, etc.)
"""

# Python imports
import asyncio, threading
# Extron Library imports

# Project imports
from modules.libraries.websockets.asyncio.server import serve, ServerConnection

def Initialize():
    #Create websocket listen thread
    threading.Thread(target=listen, args=[echo, 50555], daemon=True).start()
    print('System Initialised')

    
def listen(behaviour, port: int):
    async def start_listen(behaviour, port: int):
        await serve(behaviour, "", port)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    loop.run_until_complete(start_listen(behaviour, port))
    loop.run_forever()
        


#Websocket Behaviour
async def echo(websocket: ServerConnection):
    print(f'{websocket.id} Connected from {websocket.remote_address}')
    async for message in websocket:
        await websocket.send(message)
    print(f'{websocket.id} Disconnected')