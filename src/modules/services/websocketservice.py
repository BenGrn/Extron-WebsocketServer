from dataclasses import dataclass
from http import HTTPStatus
import json
import asyncio, threading, logging
from typing import List
from modules.intravision.core import System, DeviceBase, ServiceBase, SystemUpdateEvent, DeviceUpdateEvent, ServiceUpdateEvent
from modules.libraries.websockets.asyncio.server import serve, ServerConnection, Request

@dataclass
class WebsocketMessage:
    Event: str
    Data: any
    SystemID: str

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
        self.behaviour = self.echo_behaviour 
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
            self._send_event(client, WebsocketMessage('Initialisation', args.system, client.system_id))


    def _handle_device_update(self, sender: DeviceBase, args: DeviceUpdateEvent) -> None:
        systems = [system for system in self._systems if args.device in system.devices]
        clients = [client for client in self._clients if len([system for system in systems if system.id == client.system_id]) > 0]
        for client in clients:
            self._send_event(client, WebsocketMessage('DeviceUpdate', args.device, client.system_id))

    def _handle_service_update(self, sender: ServiceBase, args: ServiceUpdateEvent) -> None:
        systems = [system for system in self._systems if args.service in system.services]
        clients = [client for client in self._clients if len([system for system in systems if system.id == client.system_id]) > 0]
        for client in clients:
            self._send_event(client, WebsocketMessage('ServiceUpdate', args.service, client.system_id))

    def _send_event(self, client: WebsocketClient, message: WebsocketMessage) -> None:
        client.server_connection.send(json.dumps(message))

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
           return connection.respond(HTTPStatus.OK, json.dumps(self._systems))
        return connection.respond(HTTPStatus.NOT_FOUND, "Path not found")


    async def _listen(self, stop) -> None:
        logging.info(f'Websocket server started on port {self.port}')
        async with serve(self.behaviour, self.host, self.port, process_request = self._process_request):
            await stop
        logging.info(f'Websocket on port {self.port} stopped')

    async def intravision_control_behaviour(self, websocket: ServerConnection) -> None:
        pass


    async def echo_behaviour(self, websocket: ServerConnection) -> None:
        """Default echo websocket behaviour for testing."""
        logging.info(f'{websocket.id} Connected from {websocket.remote_address}')
        async for message in websocket:
            await websocket.send(message)
        logging.info(f'{websocket.id} Disconnected')