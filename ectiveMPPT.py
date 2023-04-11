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

    batteryCurrent = round(twoBytes(data, 2) / 10, 1)
    print(f'battery current: {batteryCurrent}A')

    batteryVoltage = round(twoBytes(data, 4) / 100, 2)
    print(f'battery voltage: {batteryVoltage}V')

    assistantBatteryCurrent = round(twoBytes(data, 6) / 10, 1)
    print(f'assistantBatteryCurrent: {assistantBatteryCurrent}A')

    assistantBatteryVoltage = round(twoBytes(data, 8) / 100, 2)
    print(f'assistantBatteryVoltage: {assistantBatteryVoltage}V')

    solarPanelPower = round(twoBytes(data, 10))
    print(f'solar panel power {solarPanelPower}W')

    solarPanelVoltage = round(twoBytes(data, 12) / 10, 1)
    print(f'solar panel voltage {solarPanelVoltage}V')

    loadCurrent = round(twoBytes(data, 14) / 10, 1)
    print(f'load current {loadCurrent}A')

    loadVoltage = round(twoBytes(data, 16) / 10, 1)
    print(f'load voltage {loadVoltage}V')

    loadPower = round(twoBytes(data, 18))
    print(f'load power {loadPower}W')

    DefaultDelegation.waitingForData = False

    
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
