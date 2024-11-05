from dataclasses import dataclass
from uuid import uuid5, NAMESPACE_X500
from typing import List
from .device import DeviceBase
from .service import ServiceBase
from .event import Event

@dataclass
class SystemUpdateEvent:
    system: 'System'

class System:
    def __init__(self, name):
        self.id: str = uuid5(NAMESPACE_X500, name)
        self.name: str = name
        self.devices: List[DeviceBase]
        self.services: List[ServiceBase]
        self.system_update: Event = Event(self)
    
    def request_update(self):
        self.system_update.invoke(self, SystemUpdateEvent(self))