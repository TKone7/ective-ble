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
bmsNotifyHandles=[b'\x00\x16', b'\x00\x18']
writeHandlers=[int.from_bytes(b'\x00\x19', 'big'), int.from_bytes(b'\x00\x17', 'big')]

class DefaultDelegation(btle.DefaultDelegate):
  SOI = 1
  INFO = 2
  EOI = 3
  DataType = SOI
  BufSize = 122
  Buf = bytearray(BufSize)
  Index = 0
  End = 0
  ProtocolHead = 94
  ProtocolEnd = 0

  def __init__(self):
    btle.DefaultDelegate.__init__(self)
            
  def handleNotification(self, cHandle, data):
    if args.v: print(f"handler: {cHandle} data: {data.hex()}")
    if not cHandle in [int.from_bytes(handle, 'big') for handle in bmsNotifyHandles]:
      return

    if data is None or len(data) <= 0:
      return
    
    dataString = ""

    for i in range(len(data)):
      if self.Index > self.BufSize-1:
        self.Index = 0
        self.End = 0
        self.DataType = self.SOI
      
      if self.DataType != self.SOI:
        if self.DataType == self.INFO:

          self.Buf[self.Index] = data[i]
          self.Index += 1

          if data[i] == self.ProtocolEnd:
            if (self.End < 110):
              self.End = self.Index
            if self.Index == 121 or self.Index == 66 or self.Index == 8:
              self.DataType = self.EOI
        elif self.DataType == self.EOI:
          self.End = 114
          check = 0
          
          # calculate checksum
          for j in range(1, self.End-5, 2):
            check += asciiToChar(self.Buf[j], self.Buf[j+1])

          if check == (asciiToChar(self.Buf[self.End-5], self.Buf[self.End-4]) << 8) + asciiToChar(self.Buf[self.End-3], self.Buf[self.End-2]):
            try:
              dataBuf = self.Buf[1:self.Index + 1]
              dataString = str(dataBuf, 'utf-8')

              if args.v > 1: print(dataString)

              rawdat = {}
              if args.v > 1: print(dataString[28:28+4])
              mSoc = struct.unpack('h', bytes.fromhex(dataString[28:28+4]))[0]
              rawdat['soc'] = mSoc
              if args.v > 1: print(dataString[0:8])
              mVolt = struct.unpack('i', bytes.fromhex(dataString[0:8]))[0]
              rawdat['volt'] = mVolt / 1000
              if args.v > 1: print(dataString[8:8+8])
              mCurrent = struct.unpack('i', bytes.fromhex(dataString[8:8+8]))[0]
              rawdat['current'] = mCurrent / 1000
              if args.v > 1: print(dataString[16:16+8])
              mCapacity = struct.unpack('i', bytes.fromhex(dataString[16:16+8]))[0]
              rawdat['cap'] = mCapacity / 1000
              if args.v > 1: print(dataString[24:24+4])
              cycle = struct.unpack('h', bytes.fromhex(dataString[24:24+4]))[0]
              rawdat['cycles'] = cycle
              if args.v > 1: print(dataString[32:32+4])
              kelvin = struct.unpack('h', bytes.fromhex(dataString[32:32+4]))[0]
              rawdat['temp'] = (kelvin - 2731) / 10

              print (json.dumps(rawdat, indent=1, sort_keys=False))

              # publish mqtt message as JSON string
              publish(client, json.dumps(rawdat, indent=1, sort_keys=False), f"connector/device/{args.device.replace(':', '')}")
            except ValueError as e:
              if args.v: print("caught value error")
              pass

          self.Index = 0
          self.End = 0
          self.DataType = self.SOI
      
      elif data[i] == self.ProtocolHead:
        self.DataType = self.INFO
        self.Buf[self.Index] = data[i]
        self.Index += 1

def asciiToChar(a, b):
  def valueOfAscii(val):
    if val >= 48 and val <= 57:
      return val - 48
    elif val >=65 and val <= 70:
      return val - 55
    else:
      return 0

  return (valueOfAscii(a) << 4) + valueOfAscii(b)
    

# Command line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", dest = "device", help="Specify remote Bluetooth address", metavar="MAC", default=os.getenv('DEVICE_MAC',))
parser.add_argument("-v", "--verbose", dest = "v", help="Verbosity", action='count', default=0)
args = parser.parse_args()


# test data
# d = DefaultDelegation()
# d.handleNotification(24, bytes.fromhex('30303035353500000000000000005e3545'))
# d.handleNotification(24, bytes.fromhex('33383030303044433041303030303430'))
# d.handleNotification(24, bytes.fromhex('304430333030303830303634'));
# d.handleNotification(24, bytes.fromhex('30303331304230303838303744303038'));
# d.handleNotification(24, bytes.fromhex('30453232304535463045443530443030'));
# d.handleNotification(24, bytes.fromhex('30303030303030303030303030303030'));
# d.handleNotification(24, bytes.fromhex('30303030303030303030303030303030'));
# d.handleNotification(24, bytes.fromhex('303030303030303030303030'));
# d.handleNotification(24, bytes.fromhex('30303035363800000000000000005e3545'));

# connect to broker
client = connect_mqtt()

# connects to device
if args.v: print(f"Trying to connect to {args.device}")
p = btle.Peripheral(args.device, iface=1)

# register delegate object that is called to handle notifications
p.setDelegate(DefaultDelegation())

# write 0x1000 to the handle 0x0019 to trigger the reception of notifications
if args.v: print(f"Subscribe for notifications")
for h in writeHandlers:
  try:
    p.writeCharacteristic(h, b'\x01\x00', True)
  except:
    pass

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
