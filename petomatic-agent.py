import os
import time
import usb.core
import usb.util
import json
import httplib
import RPi.GPIO as GPIO
import serial
import threading

usbip_server = "10.0.5.1"
#stat_host = "10.0.5.19"
stat_host = "128.107.33.219"
stat_port = "8080"
serial_port = "/dev/ttyACM0"
serial_speed = 9600

#prox_threshold = 600
prox_threshold = 280

usleep = lambda x: time.sleep(x/1000000.0)

class DoorStates:
    Open, Closed, Opening, Closing = range(4)

door_state = DoorStates.Closed

tmp_pos = 10.0
closed_pos = 4.5
aopen_pos = 8.0
bopen_pos = 1.0
interval = 0.5

GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
pwm = GPIO.PWM(18, 100)

def close_door():
    global door_state
    print "Close the door, my friend!"
    door_state = DoorStates.Closing
    pwm.start(tmp_pos)
    time.sleep(interval)
    pwm.ChangeDutyCycle(closed_pos)
    time.sleep(interval)
    pwm.ChangeDutyCycle(closed_pos)
    time.sleep(interval)
    door_state = DoorStates.Closed
    pwm.stop()

close_door()

ser = serial.Serial(serial_port, serial_speed, timeout = 5)

config = {}

def normalize(value):
    norm_value = value
    return int(norm_value)


def update_config():
    global config
    config = {}

    print "Fetching configuration"

    conn = httplib.HTTPConnection(stat_host, port=stat_port, timeout=10)
    conn.request(method = "GET",
                    url = "/config")
    json_string = conn.getresponse()
    data = json.load(json_string)
    print json.dumps(data, separators=(',', ': '))
    for pet in data:
        config[pet['dongle_id']] = pet
    print config

def config_worker():
    while True:
        update_config()
        time.sleep(5)

def send_stats():
    event = {}

    if (door_state == DoorStates.Open):
        event['event'] = 'doorOpened'
    else:
        event['event'] = 'doorClosed'

    event['timestamp'] = int(time.time())

    weight = read_weight();

    if (weight):
        event['weight'] = weight

    json_string = json.dumps(event, indent = 4)

    conn = httplib.HTTPConnection(stat_host, port=stat_port, timeout=10)
    conn.request(method = "POST",
                    url = "/event",
                    body = json_string)
    print conn.getresponse()

    return

def open_door(dispenser):
    global door_state
    print "Open the door " + str(dispenser) + ", my friend!"
    door_state = DoorStates.Opening
    cycle = 1
    if dispenser == 1:
        cycle = aopen_pos
    else:
        cycle = bopen_pos

    pwm.start(tmp_pos)
    time.sleep(interval)
    pwm.ChangeDutyCycle(cycle)
    time.sleep(interval)
    pwm.stop()

    door_state = DoorStates.Open
    send_stats()
    return

    door_state = DoorStates.Closed
    send_stats()
    return

def read_weight():
    print "Writing to Arduino"
    ser.write('w\r\n')
    time.sleep(1)
    print "Writing to Arduino"
    out = ""
    while ser.inWaiting() > 0:
        out += ser.read(1)
    print out
    return int(out[:-5])

def read_tag():
    print "Writing to Arduino"
    ser.write('t\r\n')
    time.sleep(1)
    print "Reading from Arduino"
    out = ""
    while ser.inWaiting() > 0:
        out += ser.read(1)
    print "(" + out + ")"
    if (out != ""):
        return int(out)
    else:
        return 0

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
        #print(logstring)
        if (checkdata > prox_threshold):
            if (door_state == DoorStates.Closed):
                tag = read_tag()
                if (tag):
                    if config[tag]:
                        open_door(config[tag]['dispenser_id'])
        else:
            if (door_state == DoorStates.Open):
                close_door()

        usleep(100)

def main():
    t = threading.Thread(target=config_worker)
    t.start()
    sensor_worker()
    t.join()

if __name__ == "__main__":
        main()
