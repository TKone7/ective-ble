import struct
from bluepy import btle
import argparse
import json
import signal
import threading

# Some handle id constants
bmsNotifyHandle=b'\x00\x18'
bmsWriteHandle=b'\x00\x19'

# setup some exit event
exit_event = threading.Event()

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


  def __init__(self):
    btle.DefaultDelegate.__init__(self)
            
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
            print (json.dumps(rawdat, indent=1, sort_keys=False))

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
      print("Waiting...")
  finally:
    print("Disconnecting...")
    p.disconnect()

# Command line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-bmsd", "--bms-device", dest = "bmsDevice", help="Specify remote Bluetooth address", metavar="MAC", required=False)
parser.add_argument("-v", "--verbose", dest = "v", help="Verbosity", action='count', default=0)
args = parser.parse_args()

# make sure we die gracefully
def signal_handler(signum, frame):
    exit_event.set()

signal.signal(signal.SIGINT, signal_handler)

# start bms thread
bmsThread = threading.Thread(target=connectAndListen, args=(args.bmsDevice,BmsDelegation(),int.from_bytes(bmsWriteHandle, 'big'),b'\x01\x00',))
bmsThread.start()


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

