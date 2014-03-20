"""
General model of the machine, including its communications route.
"""
from datetime import datetime, time
import time
import requests
import serial
import thread
from euclid import Vector2
from polarweb.models.geometry import Rectangle
from serial.tools import list_ports


class Machines(dict):
    def __init__(self, *args, **kwargs):
        super(Machines, self).__init__(*args, **kwargs)
        self.__dict__ = self

        m1 = Polargraph("left",
                        Rectangle(Vector2(305, 450), Vector2(0, 0)),
                        page={'name': 'A4',
                              'page_extent': Rectangle(Vector2(210, 297), Vector2(55, 60))},
                        com_port="COM18")
        m2 = Polargraph("right", Rectangle(Vector2(305, 450), Vector2(0, 0)),
                        page={'name': 'A4',
                              'page_extent': Rectangle(Vector2(210, 297), Vector2(55, 60))},
                        com_port="COM22")

        self[m1.name] = m1
        self[m2.name] = m2
        self.machine_names = [m1.name, m2.name]
        self.ports = list(list_ports.comports())


class Polargraph():
    """
    There's going to be a threaded / multiprocess thing going on here.

    """

    def __init__(self, name, extent, page, com_port=None):
        self.name = name
        self.extent = extent
        self.current_page = page

        self.comm_queue = CommandQueue(com_port)
        self.calibrated = False
        self.ready = False
        self.page_started = False

        self.last_move = datetime.now()
        self.contacted = datetime.now()
        self.started_time = datetime.now()
        self.set_layout('1off')

        self.status = 'idle'

        self.auto_acquire = False
        self.drawing = False

    def command_queue(self):
        return self.comm_queue

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
                'layout': self.current_layout['name'],
                'page': self.current_page['name']}

    def set_layout(self, layout_name):
        if layout_name:
            # set layout
            self.current_layout = {'name': layout_name,
                                   'panels': self._load_panels_for_layout(layout_name)}

    def _load_panels_for_layout(self, name):
        if name == '1off':
            return [self.current_page]
        if name == '2off':
            return [Rectangle(Vector2(self.current_page.size.x/2, self.current_page.size.y),
                              Vector2(0, 0)),
                    Rectangle(Vector2(self.current_page.size.x/2, self.current_page.size.y),
                              Vector2(self.current_page.size.x/2, 0))]

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
            pass
        elif command == 'pause':
            pass
        elif command == 'cancel_panel':
            pass
        elif command == 'cancel_page':
            pass
        elif command == 'retry_panel':
            pass

        return self.state()

    def acquire(self):
        """  MEthod that will acquire an image to draw.
        """
        response = requests.get("localhost:5001/api/acquire")


from serial.serialutil import SerialException
import Queue


class CommandQueue():

    def __init__(self, com_port):
        self.queue = Queue.Queue()
        self.incoming_queue = Queue.Queue()
        self.connected = False
        self.com_port = com_port

        # Init the serial io
        self.setup_com_port()
        if self.connected:
            self.start_reading()

    def __str__(self):
        return "Command Queue on port %s" % self.serial.port

    def setup_com_port(self):
        try:
            self.serial = serial.Serial(self.com_port)
            self.connected = True
            print "Connected successfully to %s (%s)." % (self.com_port, self.serial)

        except SerialException as se:
            print "Oh there was an exception loading the port %s" % self.com_port
            print se.message
            self.connected = False
            self.serial = None

    def start_reading(self):
        thread.start_new_thread(self._read_line, (None, self.incoming_queue))

    def _read_line(self, freq, queue):
        while True:
            l = self.serial.readline().strip('\r\n')
            queue.put(l)
            print "%s. %s" % (queue.qsize(), l)
            if freq:
                time.sleep(freq)

    def get_incoming_queue(self):
        return self.queue