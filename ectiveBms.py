import struct
from bluepy import btle
import argparse

# Some handle id constants
notifyHandle=b'\x00\x18'
writeHandle=b'\x00\x19'

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
    if not cHandle == int.from_bytes(notifyHandle, 'big'):
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

            # extract signed values
            mSoc = struct.unpack('h', bytes.fromhex(dataString[28:28+4]))[0]
            print(f"SOC {mSoc}%")
            mVolt = struct.unpack('i', bytes.fromhex(dataString[0:8]))[0]
            print(f"Voltage {mVolt / 1000}V")
            mCurrent = struct.unpack('i', bytes.fromhex(dataString[8:8+8]))[0]
            print(f"current {mCurrent / 1000}A")
            mCapacity = struct.unpack('i', bytes.fromhex(dataString[16:16+8]))[0]
            print(f"Capacity {mCapacity / 1000}Ah")
            cycle = struct.unpack('h', bytes.fromhex(dataString[24:24+4]))[0]
            print(f"Cycles {cycle}")
            kelvin = struct.unpack('h', bytes.fromhex(dataString[32:32+4]))[0]
            print(f"Temperature: {(kelvin - 2731) / 10} C")

          self.Index = 0
          self.End = 0
          self.DataType = self.SOI
      
      elif data[i] == self.ProtocolHead:
        self.DataType = self.INFO
        self.Buf[self.Index] = data[i]
        self.Index += 1

    if dataString:
      print(dataString)


def asciiToChar(a, b):
  def valueOfAscii(val):
    if val >= 48 and val <= 57:
      return val - 48
    elif val >=65 and val <= 70:
      return val - 55
    else:
      return 0

  return (valueOfAscii(a) << 4) + valueOfAscii(b)
    
# if __name__ == "__main__":
#   d = DefaultDelegation()
#   d.handleNotification(24, bytes.fromhex('30303035353500000000000000005e3545'))
#   d.handleNotification(24, bytes.fromhex('33383030303044433041303030303430'))
#   d.handleNotification(24, bytes.fromhex('304430333030303830303634'));
#   d.handleNotification(24, bytes.fromhex('30303331304230303838303744303038'));
#   d.handleNotification(24, bytes.fromhex('30453232304535463045443530443030'));
#   d.handleNotification(24, bytes.fromhex('30303030303030303030303030303030'));
#   d.handleNotification(24, bytes.fromhex('30303030303030303030303030303030'));
#   d.handleNotification(24, bytes.fromhex('303030303030303030303030'));
#   d.handleNotification(24, bytes.fromhex('30303035363800000000000000005e3545'));
#   exit

# Command line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", dest = "device", help="Specify remote Bluetooth address", metavar="MAC", required=True)
parser.add_argument("-v", "--verbose", dest = "v", help="Verbosity", action='count', default=0)
args = parser.parse_args()

# connects to device
if args.v: print(f"Trying to connect to {args.device}")
p = btle.Peripheral(args.device)

# register delegate object that is called to handle notifications
p.setDelegate(DefaultDelegation())

# write 0x1000 to the handle 0x0019 to trigger the reception of notifications
if args.v: print(f"Subscribe for notifications")
p.writeCharacteristic(int.from_bytes(writeHandle, 'big'), b'\x01\x00', True)

while True:
    if p.waitForNotifications(1.0):
        continue
    print("Waiting...")
