import os
import time
import usb.core
import usb.util
import threading
import json
import httplib

usbip_server = "10.0.5.1"
stat_host = "10.0.5.19"
stat_port = "8080"

prox_threshold = 600

usleep = lambda x: time.sleep(x/1000000.0)

class DoorStates:
    Open, Closed, Opening, Closing = range(4)

door_state = DoorStates.Closed

def normalize(value):
    norm_value = value
    return int(norm_value)

def send_stats():
    event = {}

    if (door_state == DoorStates.Open):
        event['event'] = 'doorOpened'
    else:
        event['event'] = 'doorClosed'

    event['timestamp'] = time.time()

    json_string = json.dumps(event, indent = 4)

    conn = httplib.HTTPConnection(stat_host, port=stat_port, timeout=10)
    conn.request(method = "POST",
                    url = "/event",
                    body = json_string)
    print conn.getresponse()

    return

def open_door():
    global door_state
    print "Open the door, my friend!"
    door_state = DoorStates.Opening
    # XXX Send Signal to Arduino
    door_state = DoorStates.Open
    send_stats()
    return

def close_door():
    global door_state
    print "Close the door, my friend!"
    door_state = DoorStates.Closing
    # XXX Send Signal to Arduino
    door_state = DoorStates.Closed
    send_stats()
    return

def sensor_worker():
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

    i = 0
    while True:
        data = dev.read(1, endpoint.wMaxPacketSize)
        data0 = (data[0x0b] | ((data[0x0c] & 0xf0) << 4))
        data1 = (data[0x0d] | ((data[0x0c] & 0x0f) << 8))
        checkdata = normalize(data1)
        logstring = "[" + str(door_state) + "] " + str(checkdata)
        # Print out the normalized data
        print(logstring)
        if (checkdata > prox_threshold):
            if (door_state == DoorStates.Closed):
                open_door()
        else:
            if (door_state == DoorStates.Open):
                close_door()

        usleep(100)

def main():
    threads = []
    t = threading.Thread(target=sensor_worker)
    threads.append(t)
    t.start()
    #for t in threading.enumerate():
    #    t.join()

if __name__ == "__main__":
        main()
