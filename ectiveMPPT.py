import struct
from bluepy import btle
import argparse
import json

# Some handle id constants
notifyHandle=b'\x00\x06'
writeHandle=b'\x00\x09'

class DefaultDelegation(btle.DefaultDelegate):
  waitingForData = True

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

    DefaultDelegation.waitingForData = False
    print (json.dumps(rawdat, indent=1, sort_keys=False))

    
def oneByte(b, start):
  i = b[start]
  l = struct.unpack('b', bytes([i]))
  return l[0]

def twoBytes(b, start):
  i = struct.unpack('>h', b[start:start+2])
  return i[0]


# Command line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", dest = "device", help="Specify remote Bluetooth address", metavar="MAC", required=True)
parser.add_argument("-v", "--verbose", dest = "v", help="Verbosity", action='count', default=0)
args = parser.parse_args()


# test data
# d = DefaultDelegation()
# d.handleNotification(6, bytearray.fromhex('ffe2006e053600000000009b0195000000850000'))
# d.handleNotification(6, bytearray.fromhex('ffe2005c05300000000000a70000000000000000'))

# connects to device
if args.v: print(f"Trying to connect to {args.device}")
p = btle.Peripheral(args.device)

# register delegate object that is called to handle notifications
p.setDelegate(DefaultDelegation())

# write to the handle 0x0009 to trigger the reception of notifications
if args.v: print(f"Subscribe for notifications")
p.writeCharacteristic(int.from_bytes(writeHandle, 'big'), b'\xff\xe2\x02\xe4', True)

while DefaultDelegation.waitingForData:
    if p.waitForNotifications(1.0):
        continue
    print("Waiting...")

# cleanup
p.disconnect()
