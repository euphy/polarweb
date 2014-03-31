"""
General model of the machine, including its communications route.
"""
from collections import deque
from datetime import datetime, time
import os
from random import randint
import time
import requests
import serial
import thread
from xml.dom import minidom
from euclid import Vector2
from polarweb.models.geometry import Rectangle, Layout
from serial.tools import list_ports


class Machines(dict):
    def __init__(self, *args, **kwargs):
        super(Machines, self).__init__(*args, **kwargs)
        self.__dict__ = self

        self.list_ports()

        m1 = Polargraph("left",
                        Rectangle(Vector2(305, 450), Vector2(0, 0)),
                        page={'name': 'A4',
                              'extent': Rectangle(Vector2(210, 297), Vector2(55, 60))},
                        comm_port="COM3")
        m2 = Polargraph("right",
                        Rectangle(Vector2(305, 450), Vector2(0, 0)),
                        page={'name': 'A4',
                              'extent': Rectangle(Vector2(210, 297), Vector2(55, 60))},
                        comm_port="COM22")

        self[m1.name] = m1
        self[m2.name] = m2
        self.machine_names = [m1.name, m2.name]

        self['indicator'] = AcquireIndicator(comm_port="COM7")


    def list_ports(self):
        self.ports = list(list_ports.comports())
        print "Com ports: %s" % self.ports
        return self.ports

class AcquireIndicator():
    def __init__(self, comm_port):
        self.comm_port = comm_port

    def setColour(self, r, g, b):
        pass

class PolargraphImageGetter():
    """
    Off-line implementation of the image getter. The PIG. See.
    """
    def __init__(self):
        pass


    def get(self, key=None):
        if key:
            # lookup existing file
            print "Key: %s" % key
            filepath = os.path.abspath(os.path.join("..\svg", key))
            print filepath
            print "is file: %s" % os.path.isfile(filepath)
            xmldoc = minidom.parse(filepath)
            i = 0
            paths = []
            for el in xmldoc.getElementsByTagName('path'):
                i += 1
                path_string = el.getAttribute('d')
                splitted = path_string.split(" ")
                couplets = []
                for bit in splitted:
                    if bit == 'z':
                        couplets.append(couplets[0])
                        break
                    elif bit in 'Lm':
                        continue

                    coords = bit.split(",")
                    coord = (float(coords[0]), float(coords[1]))
                    couplets.append(coord)

                paths.append(couplets)

            print paths
            return paths
        else:
            # capture a new file
            pass


class Polargraph():
    """
    There's going to be a threaded / multiprocess thing going on here.

    """

    def __init__(self, name, extent, page, comm_port=None):
        self.name = name
        self.extent = extent
        self.current_page = page
        self.comm_port = comm_port

        self.set_layout(page['extent'], '2x2')
        self.connected = False
        self.contacted = False
        self.calibrated = False
        self.ready = False
        self.page_started = False

        self.last_move = None
        self.started_time = datetime.now()

        self.status = 'idle'

        self.auto_acquire = False
        self.drawing = False
        self.queue_running = False
        self.position = None

        self.serial = None
        self.queue = deque(['C17,400,400,END'])
        self.received_log = deque()
        self.reading = False

        self.paths = PolargraphImageGetter().get('drawing-1.svg')

        # Init the serial io
        self.setup_comm_port()


    def setup_comm_port(self):
        try:
            self.serial = serial.Serial(self.comm_port)
            self.connected = True
            self.reading = True
            print "Connected successfully to %s (%s)." % (self.comm_port, self.serial)
            thread.start_new_thread(self._read_line, (None, self.received_log))
            thread.start_new_thread(self._write_line, (None, self.queue))
            return True

        except Exception as e:
            print "Oh there was an exception loading the port %s" % self.comm_port
            print e.message
            self.connected = False
            self.serial = None
            return False

    def _read_line(self, freq, received_log):
        while True:
            if self.reading:
                l = self.serial.readline().strip('\r\n')
                self.process_incoming_message(l)
                received_log.append(l)
                print "%s. %s" % (len(received_log), l)
            if freq:
                time.sleep(freq)

    def _write_line(self, freq, outgoing_queue):
        while True:
            if self.ready and self.queue_running:
                self.reading = False
                if outgoing_queue:
                    c = outgoing_queue.popleft()
                    self.serial.write(c+";")
                    print "Writing out: %s" % c
                    self.ready = False
                self.reading = True
            if freq:
                time.sleep(freq)


    def uptime(self):
        """
        Returns the time since starting
        """
        d = datetime.now() - self.started_time
        s = d.seconds
        hours, remainder = divmod(s, 3600)
        minutes, seconds = divmod(remainder, 60)
        return hours, minutes, seconds

    def state(self):
        return {'name': self.name,
                'calibrated': self.calibrated,
                'ready': self.ready,
                'last_move': self.last_move,
                'uptime': self.uptime(),
                'contacted': self.contacted,
                'page': self.current_page['name']}

    def control_acquire(self, command):
        if command == 'automatic':
            self.auto_acquire = True
            self.acquire()
        elif command == 'manual':
            self.auto_acquire = False
        elif command == 'now':
            self.acquire()

        return self.state()

    def control_drawing(self, command):
        if command == 'run':
            self.queue_running = True
        elif command == 'pause':
            self.queue_running = False
        elif command == 'cancel_panel':
            self.queue.clear()
            self.layout.remove_panel()
            pass
        elif command == 'cancel_page':
            self.queue.clear()
            self.queue_running = False
            self.auto_acquire = False
            self.layout.clear_panels()
        elif command == 'reuse_panel':
            self.queue.clear()

        return self.state()

    def control_pen(self, command):
        if command == 'up':
            self.queue.append("C14,0,END")
        elif command == 'down':
            self.queue.append("C13,200,END")

        return self.state()

    def calibrate(self):
        self.queue.append("C48,END")
        return self.state()

    def acquire(self):
        """  Method that will acquire an image to draw.
        """
        svg = PolargraphImageGetter.get()
        response = requests.get("localhost:5001/api/acquire")

    def process_incoming_message(self, command):
        """
        Receives messages from the machine and deals with them. This will involve:
        * raising errors
        * confirmations of updates
        * setting status
        """
        if 'READY_300' in command:
            self.contacted = True
            self.ready = True
        elif 'CARTESIAN' in command:
            self.calibrated = True
            self.position = Polargraph.unpack_sync(command)

    @classmethod
    def unpack_sync(cls, command):
        splitted = command.split(",")
        return Vector2(splitted[1], splitted[2])

    def set_layout(self, page, layout_name):
        self.layout = Layout(page, layout_name)
        self.layout.use_random_panel()

