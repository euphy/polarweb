"""
General model of the machine, including its communications route.
"""
import Queue
from collections import deque
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
                        comm_port="COM18")
        m2 = Polargraph("right", Rectangle(Vector2(305, 450), Vector2(0, 0)),
                        page={'name': 'A4',
                              'page_extent': Rectangle(Vector2(210, 297), Vector2(55, 60))},
                        comm_port="COM22")

        self[m1.name] = m1
        self[m2.name] = m2
        self.machine_names = [m1.name, m2.name]
        self.ports = list(list_ports.comports())
        print "Com ports: %s" % self.ports


class Polargraph():
    """
    There's going to be a threaded / multiprocess thing going on here.

    """

    def __init__(self, name, extent, page, comm_port=None):
        self.name = name
        self.extent = extent
        self.current_page = page
        self.comm_port = comm_port

        self.connected = False
        self.contacted = False
        self.calibrated = False
        self.ready = False
        self.page_started = False

        self.last_move = None
        self.started_time = datetime.now()
        self.set_layout('1up')

        self.status = 'idle'

        self.auto_acquire = False
        self.drawing = False

        self.serial = None
        self.queue = deque(['starter', 'commands', 'here', 'for', 'example'])
        self.received_log = deque()
        self.reading = False

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

        except Exception as e:
            print "Oh there was an exception loading the port %s" % self.comm_port
            print e.message
            self.connected = False
            self.serial = None

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
            if self.ready:
                self.reading = False
                if outgoing_queue:
                    c = outgoing_queue.popleft()
                    self.serial.write(c + '\r\n')
                    print "Writing out: %s" % c
                    self.reading = True
                    self.ready = False


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
        if name == '1up':
            return [self.current_page]
        if name == '2up':
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
        elif 'SYNC' in command:
            self.calibrated = True
            self.position = Polargraph.unpack_sync(command)

    @classmethod
    def unpack_sync(cls, command):
        print command
