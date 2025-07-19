from dataclasses import dataclass
from http import HTTPStatus
import json
import asyncio, threading, logging
from typing import List, Dict
from modules.intravision.core import System, DeviceBase, ServiceBase, SystemUpdateEvent, DeviceUpdateEvent, ServiceUpdateEvent
from modules.libraries.websockets.asyncio.server import serve, ServerConnection, Request

@dataclass
class WebsocketMessage:
    Event: str
    Data: any
    SystemID: str

    def reprJSON(self) -> Dict:
        d = {k: v for k, v in self.__dict__.items()}.copy()
        for key, value in self.__class__.__dict__.items():
            if isinstance(value, property):
                d[key] = getattr(self, key)
        return d
    
    def __repr__(self):
        return str(self.reprJSON())

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj,'reprJSON'):
            return obj.reprJSON()
        else:
            return json.JSONEncoder.default(self, obj)
    
class WebsocketMessageEncoder(json.JSONEncoder):
    @classmethod
    def deserialize_websocket_message(cls, jdict: Dict):
        if 'SystemID' in jdict:
            message = WebsocketMessage(**jdict)
            return message
        else:
            return jdict

class WebsocketClient:
    def __init__(self, server_connection: ServerConnection, system_id: str) -> None:
        self.server_connection = server_connection
        self.system_id = system_id

class WebsocketService(ServiceBase):
    """A websocket server to provide communications from an Intravision front end to devices within a system."""

    def __init__(self, name):
        self._systems: List[System] = []
        self._clients: List[WebsocketClient] = []
        self._subscribed_devices: List[DeviceBase] = []
        self._subscribed_services: List[ServiceBase] = []
        self._loop = None
        self._stop = None
        self.host = ""
        self.port = 50555
        self.behaviour = self.intravision_control_behaviour
        self.quiet_logger = logging.getLogger("Quiet")
        self.quiet_logger.setLevel(logging.WARNING)
        super().__init__(name)

    def shutdown(self) -> None:
        """Stops the websocket server, disconnecting all active sessions."""
        if self._stop != None:
            self._stop.set()
            self._loop = None
    
    def start(self) -> None:
        """Starts the websocket server on host and port specified within the WebsocketService object."""
        threading.Thread(target=self._start_loop, daemon=True).start()

    def register_system(self, system: System) -> None:
        self._systems.append(system)
        system.system_update += self._handle_system_update
        for device in system.devices:
            device.device_update += self._handle_device_update
            self._subscribed_devices.append(device)
        for service in system.services:
            service.service_update += self._handle_service_update
            self._subscribed_services.append(device)
    
    def unregister_system(self, system: System) -> None:
        try:
            self._systems.remove(system)
            system.system_update -= self._handle_system_update
        except ValueError:
            logging.info(f'System {system.name} cannot be removed as it is not currently registered')

    def _handle_system_update(self, sender: System, args: SystemUpdateEvent) -> None:  
        for device in [device for device in args.system.devices if device not in self._subscribed_devices]:
            device.device_update += self._handle_device_update
            self._subscribed_devices.append(device)
        for service in [service for service in args.system.services if service not in self._subscribed_services]:
            service.service_update += self._handle_service_update
            self._subscribed_services.append(service)
        for client in [client for client in self._clients if client.system_id == args.system.id]:
            asyncio.run(self._send_event(client, WebsocketMessage('Initialisation', args.system, client.system_id)))


    def _handle_device_update(self, sender: DeviceBase, args: DeviceUpdateEvent) -> None:
        systems = [system for system in self._systems if args.device in system.devices]
        clients = [client for client in self._clients if len([system for system in systems if system.id == client.system_id]) > 0]
        for client in clients:
            asyncio.run(self._send_event(client, WebsocketMessage('DeviceUpdate', args.device, client.system_id)))

    def _handle_service_update(self, sender: ServiceBase, args: ServiceUpdateEvent) -> None:
        systems = [system for system in self._systems if args.service in system.services]
        clients = [client for client in self._clients if len([system for system in systems if system.id == client.system_id]) > 0]
        for client in clients:
            asyncio.run(self._send_event(client, WebsocketMessage('ServiceUpdate', args.service, client.system_id)))

    async def _send_event(self, client: WebsocketClient, message: WebsocketMessage) -> None:
        await client.server_connection.send(json.dumps(message, cls=ComplexEncoder))
        logging.debug(f'Sending to {client.server_connection.id}: {message}')

    def _start_loop(self) -> None:
        if self._loop != None:
            return
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop = threading.Event()
        stop = asyncio.get_event_loop().run_in_executor(None, self._stop.wait)
        #self._loop.add_signal_handler(signal.SIGTERM, stop.set_result, None) Linux Only
        self._loop.run_until_complete(self._listen(stop))
    
    async def _process_request(self, connection: ServerConnection, request: Request):
        request_headers = request.headers
        path = request.path
        if request_headers.get("Connection", None) == "Upgrade":
            return None
        if path == "/Systems":
           return connection.respond(HTTPStatus.OK, json.dumps(self._systems, cls=ComplexEncoder))
        return connection.respond(HTTPStatus.NOT_FOUND, "Path not found")

    async def _listen(self, stop) -> None:
        logging.info(f'Websocket server started on port {self.port}')
        async with serve(self.behaviour, self.host, self.port, process_request = self._process_request, logger=self.quiet_logger):
            await stop
        logging.info(f'Websocket on port {self.port} stopped')

    async def intravision_control_behaviour(self, websocket: ServerConnection) -> None:
        logging.info(f'{websocket.id} Connected from {websocket.remote_address}')
        async for message in websocket:
            logging.debug(f'Received from {websocket.id}: {message}')
            message: WebsocketMessage = json.loads(message, object_hook=WebsocketMessageEncoder.deserialize_websocket_message)
            system = next((system for system in self._systems if system.id == message.SystemID), None)
            if system is None:
                logging.error(f'System does not exist: {message.SystemID}')
            else:
                match message.Event:
                    case "Initialise":
                        client = WebsocketClient(websocket, system.id)
                        self._clients.append(client)
                        await self._send_event(client, WebsocketMessage("Initialisation", system, system.id))
                        logging.debug(f'Client {websocket.id} registered to System {system.id}')
                    case _:
                        logging.error(f'Websocket failed to get event: {message.Event}')



            """
                switch (message?.Event)
                {
                    case "Initialise":
                        InitialiseClient(system, e.Client);
                        break;
                    case "SetPower":
                        var powerMessage = (WebsocketBoolMessage)message;
                        SetSystemPower(system, powerMessage.Data);
                        break;
                    case "ControlDevice":
                        var deviceControlMessage = (WebsocketControlMessage)message;
                        ControlDevice(system, deviceControlMessage.Data);
                        break;
                    case "ControlService":
                        var serviceControlMessage = (WebsocketControlMessage)message;
                        ControlService(system, serviceControlMessage.Data);
                        break;
                    case "Error":
                        Log.Logger.Error("Failed to parse {data}", data);
                        break;
                }
            }"""


        logging.info(f'{websocket.id} Disconnected')
        
    async def echo_behaviour(self, websocket: ServerConnection) -> None:
        """Default echo websocket behaviour for testing."""
        logging.info(f'{websocket.id} Connected from {websocket.remote_address}')
        async for message in websocket:
            await websocket.send(message)
        logging.info(f'{websocket.id} Disconnected')