from abc import ABC
from dataclasses import dataclass
from datetime import datetime, timedelta
import importlib
import json
import logging
import re
from threading import Thread
from time import sleep
from typing import Dict
from uuid import NAMESPACE_X500, uuid5
from .event import Event

@dataclass
class ServiceUpdateEvent:
    device: 'ServiceBase'

class ServiceBase(ABC):
    def __init__(self, name: str = None):
        if name == None:
            raise Exception(f'{self.type} instantiated without a name')
        self.id: str = str(uuid5(NAMESPACE_X500, name))
        self.name: str = name
        self.type = type(self).__name__
        self.device_update: Event = Event(self)
        self.json_excluded_properties = [
            'device_update',
            'json_excluded_properties'
        ]

        self.__last_update = datetime.min
        self.__update_interval = timedelta(milliseconds=150)
        self.__update_thread = None

    def request_update(self):
        if datetime.now() - self.__last_update > self.__update_interval:
            self.__last_update = datetime.now()
            self.device_update.invoke(self, ServiceUpdateEvent(self))
        elif self.__update_thread == None:
            self.__update_thread = Thread(target=self.__update, daemon=True)
            self.__update_thread.start()

    def __update(self):
        sleep(self.__update_interval.total_seconds() - (datetime.now() - self.__last_update).total_seconds())
        self.device_update.invoke(self, ServiceUpdateEvent(self))
        self.__update_thread = None
    
    def update_property(self, property: str, value):
        if not hasattr(self, property):
            logging.error(f'{self.name} does not contain property: {property}')
            return
        if type(getattr(self, property)) != type(value):
            logging.error(f'{self.name} trying to set {property} of type {type(getattr(self, property))} to value of type {type(value)}')
            return
        if getattr(self, property) != value:
            setattr(self, property, value)
            self.request_update()

    def __repr__(self):
        return json.dumps(self, cls = ServiceSerialization)
    
class ServiceSerialization(json.JSONEncoder):
    def default(self, device: ServiceBase):
        def get_object_dict(obj: ServiceBase):
            d = {self.snake_to_pascal(k): v for k, v in obj.__dict__.items() if k not in obj.json_excluded_properties and not k.startswith('_')}.copy()
            for key, value in obj.__class__.__dict__.items():
                if isinstance(value, property):
                    d[self.snake_to_pascal(key)] = getattr(obj, key)
            return d
        return get_object_dict(device)
    
    def snake_to_pascal(self, s):
        a = s.split('_')
        a[0] = a[0].title()
        if len(a) > 1:
            a[1:] = [u.title() for u in a[1:]]
        return ''.join(a)
    
    @classmethod
    def deserialize_device(cls, jdict: Dict):
        if 'Type' in jdict:
            device_class =  getattr(importlib.import_module('modules.services'), jdict['Type'])
            response = device_class(jdict['Name'])
            for key, value in jdict.items():
                setattr(response, cls.__pascal_to_snake(key), value)
            return response
        else:
            return jdict
    
    @staticmethod
    def __pascal_to_snake(s) -> str:
        return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()