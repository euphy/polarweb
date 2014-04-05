"""
General model of the machine, including its communications route.
"""
from collections import deque
from datetime import datetime, time
import io
from multiprocessing import Process, Queue
import os
from random import randint
import time
import requests
import serial
import thread
from xml.dom import minidom
from euclid import Vector2
from image_grabber.lib.app import ImageGrabber
from pathfinder import sample_workflow, paths2svg
from polarweb.models.Indicator import AcquireIndicator
from polarweb.models.geometry import Rectangle, Layout
from serial.tools import list_ports


class Machines(dict):
    def __init__(self, *args, **kwargs):
        super(Machines, self).__init__(*args, **kwargs)
        self.__dict__ = self

        self.list_ports()
        self['rgb_ind'] = AcquireIndicator()

        m1 = Polargraph("left",
                        Rectangle(Vector2(705, 980), Vector2(0, 0)),
                        page={'name': 'A1',
                              'extent': Rectangle(Vector2(594, 837), Vector2(61, 85))},
                        comm_port="COM3",
                        rgb_ind=self['rgb_ind'])
        m2 = Polargraph("right",
                        Rectangle(Vector2(705, 980), Vector2(0, 0)),
                        page={'name': 'A1',
                              'extent': Rectangle(Vector2(594, 837), Vector2(61, 85))},
                        comm_port="COM18",
                        rgb_ind=self['rgb_ind'])

        self[m1.name] = m1
        self[m2.name] = m2
        self.machine_names = [m1.name, m2.name]


    def list_ports(self):
        self.ports = list(list_ports.comports())
        print "Com ports: %s" % self.ports
        return self.ports


class Polargraph():
    """
    There's going to be a threaded / multiprocess thing going on here.
    """

    camera_lock = False

    def __init__(self, name, extent, page, comm_port=None, rgb_ind=None):
        self.name = name
        self.extent = extent
        self.current_page = page
        self.comm_port = comm_port
        self.rgb_ind = rgb_ind

        self.status = 'waiting_for_new_layout'
        self.set_layout(page['extent'], '4x4')

        # To do with communications
        self.connected = False
        self.contacted = False
        self.calibrated = False
        self.ready = False
        self.page_started = False

        self.last_move = None
        self.started_time = datetime.now()


        self.auto_acquire = False
        self.drawing = False
        self.queue_running = False
        self.position = None

        self.serial = None
        self.queue = deque(['C17,400,400,END'])
        self.received_log = deque()
        self.reading = False

        self.paths = None

        # Init the serial io
        self.setup_comm_port()

        # and the event heartbeat
        drawing_thread = thread.start_new_thread(self.heartbeat, (2,))



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
                print "%s: %s. %s" % (self.name, len(received_log), l)
            if freq:
                time.sleep(freq)

    def _write_line(self, freq, outgoing_queue):
        while True:
            if self.ready and self.queue_running:
                self.reading = False
                if outgoing_queue:
                    self.status = 'serving'
                    c = outgoing_queue.popleft()
                    self.serial.write(c+";")
                    print "Writing out: %s" % c
                    if not outgoing_queue:  # that was the last one
                        self.status = 'exhausted_queue'
                    self.ready = False
                self.reading = True
            if freq:
                time.sleep(freq)




    def heartbeat(self, freq):
        """
        Setting status flags, and initiating new actions based on combinations of status flags.
        """
        while True:
            if self.status == 'exhausted_queue':
                self.layout.remove_current_panel()
                new_panel = self.layout.use_random_panel()
                if not new_panel:  # like the last panel was the final one of that layout
                    self.status = 'waiting_for_new_layout'

            if self.status == 'waiting_for_new_layout':
                self.queue_running = False

            if self.status == 'idle' \
                    and self.layout.get_current_panel():
                # these conditions indicate it's ok to acquire and start
                if self.auto_acquire:
                    print "%s OK TO START A DRAWING!" % self.name
                    self.status = 'acquiring'
                    self.acquire()

            if self.status == 'acquired' \
                    and self.layout.get_current_panel() \
                    and self.paths:
                try:
                    self.paths = self.layout.scale_to_panel(self.paths)
                    commands = self.build_commands(self.paths)
                    print "%s Appending %s commands the the queue." % (self.name, len(commands))
                    self.queue.extend(commands)
                except ValueError:
                    print "%s Problem scaling paths to the panel."
                    self.paths = None
                    self.queue.clear()

                if self.queue:
                    self.status = "serving"
                    self.layout.remove_current_panel()

            if freq:
                time.sleep(freq)

    def get_machine_as_svg(self):
        filename = os.path.abspath("%s.svg" % self.name)
        paths2svg(self.paths or {},
                  self.extent.size, filename, scale=1.0, show_nodes=True, outline=True,
                  page=self.layout.extent, panel=self.layout.get_current_panel())

        return filename

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
                'status': self.status,
                'calibrated': self.calibrated,
                'ready': self.ready,
                'last_move': self.last_move,
                'uptime': self.uptime(),
                'contacted': self.contacted,
                'page': self.current_page['name'],
                'camera_in_use': Polargraph.camera_lock,
                'current panel': str(self.layout.get_current_panel().__str__()),
                'layout design': str(self.layout.design),
                'paths': self.paths
        }

    def control_acquire(self, command):
        if command == 'automatic':
            self.auto_acquire = True
        elif command == 'manual':
            self.auto_acquire = False
        elif command == 'now':
            result = self.state()
            ac = self.acquire()
            if ac:
                result.update(self.acquire())

            return result

        return self.state()

    def control_drawing(self, command):
        if command == 'run':
            # if press run, then just use the same layout as last time
            if self.status == 'waiting_for_new_layout':
                self.set_layout(self.extent, self.layout.design)
                self.status = 'idle'
            self.queue_running = True
        elif command == 'pause':
            self.queue_running = False
        elif command == 'cancel_panel':
            self.queue.clear()
            self.queue.append("C14,0,END")  # pen lift
            self.layout.remove_current_panel()

        elif command == 'cancel_page':
            self.queue.clear()
            self.queue_running = False
            self.layout.clear_panels()
            self.status = 'waiting_for_layout'
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

    def ac(self, paths_queue):
        grabber = ImageGrabber(debug=True)
        img_filename = grabber.get_image(filename="png", rgb_ind=self.rgb_ind)
        print "Got %s" % img_filename

        paths = sample_workflow.run(input_img=img_filename, rgb_ind=self.rgb_ind)
        print paths
        for p in paths:
            paths_queue.put(p)

    def acquire(self):
        """  Method that will acquire an image to draw.
        """
        if Polargraph.camera_lock:
            print "Camera is locked. Cancelling. But come back later please!"
            self.status = 'idle'
            return {'http_code': 503}

        Polargraph.camera_lock = True
        self.paths = None
        paths_queue = Queue()

        # p = Process(target=self.ac, args=(paths_queue,))
        # p.start()
        # p.join(60)
        self.ac(paths_queue)

        self.paths = []
        paths_queue.put('STOP')
        for i in iter(paths_queue.get, 'STOP'):
            self.paths.append(i)

        if self.paths:
            self.status = 'acquired'
        else:
            self.status = 'idle'
        Polargraph.camera_lock = False

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
        if self.status == 'waiting_for_new_layout':
            self.layout = Layout(page, layout_name)
            self.layout.use_random_panel()
            self.status = 'idle'

        return {'layout': layout_name,
                'page': page}



    def build_commands(self, paths):
        result = []
        for path in paths:
            first = True
            for point in path:
                if first:
                    result.append("C14,0,END")
                    result.append("C17,%.1f,%.1f,END" % (point[0], point[1]))
                    result.append("C13,200,END")
                    first = False
                else:
                    result.append("C17,%.1f,%.1f,END" % (point[0], point[1]))

        result.append("C14,0,END")

        return result




