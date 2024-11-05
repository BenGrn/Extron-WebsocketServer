import logging, json
from modules.intravision.core import DeviceBase, DeviceSerialization
from modules.devices import DeviceA, DeviceB
from modules.services import WebsocketService

logging.getLogger().setLevel(logging.INFO)
logging.basicConfig(format='%(asctime)s - %(message)s')

# def handle_update(sender, args):
#     logging.info(args.device)

# devicea = DeviceA("DeviceA")
# deviceb = DeviceA("DeviceB")
# devicec: DeviceA = json.loads('{"Name": "DeviceC", "Type": "DeviceA"}', object_hook = DeviceSerialization.deserialize_device)
# devicea.device_update += handle_update
# deviceb.device_update += handle_update
# devicec.device_update += handle_update
# devicea.request_update()
# deviceb.request_update()
# devicec.request_update()

test_server = WebsocketService("TP Server")
test_server.start()
logging.info('Start Called')
inp = input()
test_server.shutdown()
inp == input()
logging.info('Exiting')