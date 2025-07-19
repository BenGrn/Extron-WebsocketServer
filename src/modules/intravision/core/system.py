import json, importlib, re
from dataclasses import dataclass
from uuid import uuid5, NAMESPACE_X500
from typing import List, Dict
from .device import DeviceBase
from .service import ServiceBase
from .event import Event

@dataclass
class SystemUpdateEvent:
    system: 'System'

class System:
    def __init__(self, name):
        self.id: str = str(uuid5(NAMESPACE_X500, name))
        self.name: str = name
        self.devices: List[DeviceBase] = []
        self.services: List[ServiceBase] = []
        self.system_update: Event = Event(self)
        self.json_excluded_properties = [
            'system_update',
            'json_excluded_properties'
        ]
    
    def request_update(self):
        self.system_update.invoke(self, SystemUpdateEvent(self))

    def reprJSON(self) -> Dict:
        d = {self._snake_to_pascal(k): v for k, v in self.__dict__.items() if k not in self.json_excluded_properties and not k.startswith('_')}.copy()
        for key, value in self.__class__.__dict__.items():
            if isinstance(value, property):
                d[self._snake_to_pascal(key)] = getattr(self, key)
        return d
    
    def _snake_to_pascal(self, s):
        a = s.split('_')
        a[0] = a[0].title()
        if len(a) > 1:
            a[1:] = [u.title() for u in a[1:]]
        return ''.join(a)
    
    def __repr__(self):
        return str(self.reprJSON())
    