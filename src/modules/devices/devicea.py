from modules.intravision.core.device import DeviceBase


class DeviceA(DeviceBase):
    def __init__(self, name = None):
        self.prop_a = "Test"
        self._test = "value"
        super().__init__(name)
    
    @property
    def test(self):
        return self._test
    
    @test.setter
    def test(self, value):
        self._test = value