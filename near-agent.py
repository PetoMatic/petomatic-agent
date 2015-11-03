import os
import time
import usb.core
import usb.util

usbip_server = "10.0.5.1"

def normalize(value):
    norm_value = value
    return int(norm_value)

def main():
    print "Testing IR sensor"
    os.environ["USBIP_SERVER"] = usbip_server
    dev = usb.core.find(address=int("0022BDCF4894", 16)) # find using mac address
    if dev is None:
        raise ValueError('Device not found')

 # Get the endpoint value of the device
    endpoint = dev[0][(0,0)][0]

    dev.set_configuration()
    print usb.util.get_string(dev, 256, 1)
    print usb.util.get_string(dev, 256, 2)
    print usb.util.get_string(dev, 256, 3)

# write the data
    i = 0
    while True:
        data = dev.read(1, endpoint.wMaxPacketSize)
        data0 = (data[0x0b] | ((data[0x0c] & 0xf0) << 4))
        data1 = (data[0x0d] | ((data[0x0c] & 0x0f) << 8))

        # Print out the normalized data
        print(normalize(data1))
        time.sleep(1)

if __name__ == "__main__":
        main()
