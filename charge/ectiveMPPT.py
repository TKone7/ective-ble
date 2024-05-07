import struct
from bluepy import btle
import argparse
import json
from paho.mqtt import client as mqtt_client
import random
import signal
import os

running = True
broker = os.getenv('MQTT_HOST', '127.0.0.1')
port = int(os.getenv('MQTT_PORT', 1883))
client_id = f'python-mqtt-{random.randint(0, 1000)}'

def signal_handler(signum, frame):
    global running
    running = False

signal.signal(signal.SIGINT, signal_handler)

def on_disconnect(client, userdata, rc):
    logging.info("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logging.info("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logging.info("Reconnected successfully!")
            return
        except Exception as err:
            logging.error("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)

def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
    # For paho-mqtt 2.0.0, you need to add the properties parameter.
    # def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)
    # Set Connecting Client ID
    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, client_id)

    # For paho-mqtt 2.0.0, you need to set callback_api_version.
    # client = mqtt_client.Client(client_id=client_id, callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2)

    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(broker, port)
    return client

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60


def publish(client, payload, topic, retain=False):
    result = client.publish(topic=topic, payload=payload, retain=retain)
    # result: [0, 1]
    status = result[0]
    if status == 0:
        print(f"Send `{payload}` to topic `{topic}`")
    else:
        print(f"Failed to send message to topic {topic}")

# Some handle id constants
notifyHandle=b'\x00\x06'
writeHandle=b'\x00\x09'

class DefaultDelegation(btle.DefaultDelegate):

  def __init__(self):
    btle.DefaultDelegate.__init__(self)
            
  def handleNotification(self, cHandle, data):
    if not cHandle == int.from_bytes(notifyHandle, 'big'):
      return

    if args.v: print(f"handler: {cHandle} data: {data.hex()}")

    if data is None or len(data) <= 0:
      return
    
    if not (oneByte(data, 0) == -1 and oneByte(data, 1) == -30 and len(data) == 20):
      return

    rawdat = {}

    batteryCurrent = round(twoBytes(data, 2) / 10, 1)
    rawdat['batteryCurrent'] = batteryCurrent

    batteryVoltage = round(twoBytes(data, 4) / 100, 2)
    rawdat['batteryVoltage'] = batteryVoltage

    assistantBatteryCurrent = round(twoBytes(data, 6) / 10, 1)
    rawdat['assistantBatteryCurrent'] = assistantBatteryCurrent

    assistantBatteryVoltage = round(twoBytes(data, 8) / 100, 2)
    rawdat['assistantBatteryVoltage'] = assistantBatteryVoltage

    solarPanelPower = round(twoBytes(data, 10))
    rawdat['solarPanelPower'] = solarPanelPower

    solarPanelVoltage = round(twoBytes(data, 12) / 10, 1)
    rawdat['solarPanelVoltage'] = solarPanelVoltage

    loadCurrent = round(twoBytes(data, 14) / 10, 1)
    rawdat['loadCurrent'] = loadCurrent

    loadVoltage = round(twoBytes(data, 16) / 10, 1)
    rawdat['loadVoltage'] = loadVoltage

    loadPower = round(twoBytes(data, 18))
    rawdat['loadPower'] = loadPower

    print (json.dumps(rawdat, indent=1, sort_keys=False))

    # publish mqtt message as JSON string
    publish(client, json.dumps(rawdat, indent=1, sort_keys=False), f"connector/device/{args.device.replace(':', '')}")

    
def oneByte(b, start):
  i = b[start]
  l = struct.unpack('b', bytes([i]))
  return l[0]

def twoBytes(b, start):
  i = struct.unpack('>h', b[start:start+2])
  return i[0]


# Command line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", dest = "device", help="Specify remote Bluetooth address", metavar="MAC", default=os.getenv('DEVICE_MAC'))
parser.add_argument("-v", "--verbose", dest = "v", help="Verbosity", action='count', default=0)
args = parser.parse_args()

# connect to broker
client = connect_mqtt()

# connects to device
if args.v: print(f"Trying to connect to {args.device}")
p = btle.Peripheral(args.device)

# register delegate object that is called to handle notifications
p.setDelegate(DefaultDelegation())

# write to the handle 0x0009 to trigger the reception of notifications
if args.v: print(f"Subscribe for notifications")
p.writeCharacteristic(int.from_bytes(writeHandle, 'big'), b'\xff\xe2\x02\xe4', True)

try:
  while running:
    if p.waitForNotifications(1.0):
        continue
    if args.v: print("Waiting...")
except:
  print(f"Whew! {sys.exc_info()[0]} occurred.", file=sys.stderr)
finally:
  if args.v: print("Disconnecting...")
  p.disconnect()

