import struct
from bluepy import btle
import argparse
import json
import signal
import threading

# Some handle id constants
bmsNotifyHandle=b'\x00\x18'
chargeNotifyHandle=b'\x00\x06'

# setup some exit event
exit_event = threading.Event()

class ChargeDelegation(btle.DefaultDelegate):
  waitingForData = True

  def __init__(self, mac):
    btle.DefaultDelegate.__init__(self)
    self.mac = mac
            
  def handleNotification(self, cHandle, data):
    if not cHandle == int.from_bytes(chargeNotifyHandle, 'big'):
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

    ChargeDelegation.waitingForData = False

    returnValue = {}
    returnValue[self.mac] = rawdat
    print (json.dumps(returnValue, sort_keys=False))

class BmsDelegation(btle.DefaultDelegate):
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
  waitingForData = True


  def __init__(self, mac):
    btle.DefaultDelegate.__init__(self)
    self.mac = mac
            
  def handleNotification(self, cHandle, data):
    if args.v: print(f"handler: {cHandle} data: {data.hex()}")
    if not cHandle == int.from_bytes(bmsNotifyHandle, 'big'):
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
            dataBuf = self.Buf[1:self.Index + 1]
            dataString = str(dataBuf, 'utf-8')

            if args.v > 1: print(dataString)

            # there are errors while reading bytes
            # just continue if it happens
            try:
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

              BmsDelegation.waitingForData = False

              returnValue = {}
              returnValue[self.mac] = rawdat
              print (json.dumps(returnValue, sort_keys=False))
            except:
              if args.v: print('Error while reading bytes, continue listeing')

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
    
def oneByte(b, start):
  i = b[start]
  l = struct.unpack('b', bytes([i]))
  return l[0]

def twoBytes(b, start):
  i = struct.unpack('>h', b[start:start+2])
  return i[0]

def connectAndListen(device, delegation, handle, value):
  # connects to device
  if args.v: print(f"Trying to connect to {device}")
  p = btle.Peripheral(device)

  # register delegate object that is called to handle notifications
  p.setDelegate(delegation)

  if args.v: print(f"Subscribe for notifications")
  p.writeCharacteristic(handle, value, True)

  try:
    while True:
      if exit_event.is_set():
        break
      if p.waitForNotifications(1.0):
          continue
      if args.v: print("Waiting...")
  finally:
    if args.v: print("Disconnecting...")
    p.disconnect()

# Command line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-bmsd", "--bms-device", dest = "bmsDevice", help="Specify a list of BMS devices (MAC) to observe the status", nargs="*", metavar="MAC", required=False)
parser.add_argument("-charged", "--charge-device", dest = "chargeDevice", help="Specify a list of charge devices (MAC) to observe the status", nargs="*", metavar="MAC", required=False)
parser.add_argument("-v", "--verbose", dest = "v", help="Verbosity", action='count', default=0)
args = parser.parse_args()

# make sure we die gracefully
def signal_handler(signum, frame):
    exit_event.set()

signal.signal(signal.SIGINT, signal_handler)

# start bms threads
for bmsDevice in args.bmsDevice or []:
  bmsThread = threading.Thread(target=connectAndListen, args=(bmsDevice,BmsDelegation(bmsDevice),int.from_bytes(b'\x00\x19', 'big'),b'\x01\x00',))
  bmsThread.start()

for chargeDevice in args.chargeDevice or []:
  chargeThread = threading.Thread(target=connectAndListen, args=(chargeDevice,ChargeDelegation(chargeDevice),int.from_bytes(b'\x00\x09', 'big'),b'\xff\xe2\x02\xe4',))
  chargeThread.start()
