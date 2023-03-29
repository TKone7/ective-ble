from bluepy import btle
import argparse

def asciiToChar(a, b):
  def valueOfAscii(val):
    val = int.from_bytes(val, 'little')

    if val >= 48 and val <= 57:
      return val - 48
    elif val >=65 and val <= 70:
      return val - 55
    else:
      return 0

  return (valueOfAscii(a) << 4) + valueOfAscii(b)
    

if __name__ == "__main__":
  print(asciiToChar(b'\x46', b'\x30'))
  exit

# Some handle id constants
notifyHandle=b'\x00\x18'
writeHandle=b'\x00\x19'

# Command line parameters
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", dest = "device", help="Specify remote Bluetooth address", metavar="MAC", required=True)
parser.add_argument("-v", "--verbose", dest = "v", help="Verbosity", action='count', default=0)
args = parser.parse_args()

class DefaultDelegation(btle.DefaultDelegate):
    def __init__(self):
        btle.DefaultDelegate.__init__(self)
            
    def handleNotification(self, cHandle, data):
        if cHandle == int.from_bytes(notifyHandle, 'big'):
            if args.v: print(data)

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

