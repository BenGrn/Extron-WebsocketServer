from typing import Callable

class Event:
    """An event class that mimics C# events.
    To create an event object my_event = Event().
    Default values may be passed to the event constructor if required.
    To subscribe provide a callback method to the event: my_event += callback.
    To remove subscription: my_event -= callback.
    To raise an event call: my_event.invoke(sender, event_args).
    Callback function signature must match the arguments raised.
    Callbacks are not threaded and may block."""

    def __init__(self, default_event: object = None):
        self.subscriptions: list[Callable] = []
        self._last_event = default_event  
    
    def __iadd__(self, sub):
        self.subscriptions.append(sub)
        return self
    
    def __isub__(self, sub):
        self.subscriptions.remove(sub)
        return self
    
    def invoke(self, sender: object, event: object):
        self._last_event = event
        for sub in tuple(self.subscriptions):
            sub(sender, event)
    
    def __len__(self):
        return len(self.subscriptions)

    @property
    def value(self):
        """A property to return the last event emitted."""
        return self._last_event