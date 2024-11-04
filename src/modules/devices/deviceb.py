from modules.intravision.core.device import DeviceBase


class DeviceB(DeviceBase):
    def __init__(self, name = None):
        self.prop_b = "Test"
        super().__init__(name)
        self.json_excluded_properties.append('prop_a')
        self.json_excluded_properties.append('prop_b')