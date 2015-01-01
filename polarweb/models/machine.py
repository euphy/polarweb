"""
General model of the machine, including its communications route.
"""
from collections import deque
from datetime import datetime
import os
import time
import thread

import serial
from euclid import Vector2
from serial.tools import list_ports

from polarweb.image_grabber.lib.app import ImageGrabber
from polarweb.models import acquire
from polarweb.pathfinder import paths2svg
from polarweb.models.geometry import Rectangle, Layout
from polarweb.pathfinder import workflow

from polarweb.config import SETTINGS

class Machines(dict):

    default_page=SETTINGS['pages'][SETTINGS['default_page']]
    default_page['name'] = SETTINGS['default_page']

    def __init__(self, *args, **kwargs):
        super(Machines, self).__init__(*args, **kwargs)
        self.__dict__ = self

        self.list_ports()
        self.machine_names = []
        for k, v in SETTINGS['machines'].items():
            p = Polargraph(name=k,
                           extent=v['extent'],
                           page=SETTINGS['pages'][v['default_page']],
                           comm_port=v['comm_port'],
                           acquire_method=SETTINGS['artwork_acquire'])
            self[p.name] = p
            self.machine_names.append(p.name)


    def list_ports(self):
        self.ports = list(list_ports.comports())
        print "Com ports: %s" % self.ports
        return self.ports


class Polargraph():
    """
    There's going to be a threaded / multiprocess thing going on here.
    """

    camera_lock = False

    def __init__(self, name, extent, page, comm_port=None, rgb_ind=None, artwork_acquire=None):
        self.name = name
        self.extent = extent
        self.current_page = page
        self.comm_port = comm_port
        self.rgb_ind = rgb_ind

        self.status = 'waiting_for_new_layout'
        self.set_layout(page['extent'], '3x3')

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
        self.queue = deque(['C17,400,400,10,END'])
        self.received_log = deque()
        self.reading = False

        self.paths = None

        # Init the serial io
        self.setup_comm_port()

        # and the event heartbeat
        drawing_thread = thread.start_new_thread(self.heartbeat, (2,))

        self.commands = {'pen_up': 'C14,20,END',
                         'pen_down': 'C13,130,END'}

        # set up acquire strategy
        self.can_acquire = False
        if artwork_acquire:
            try:
                self.acquire = acquire.get_acquire_func(artwork_acquire['method_name'],
                                                        artwork_acquire['module'])
                self.can_acquire = True
            except:
                self.can_acquire = False









    def setup_comm_port(self):
        try:
            self.serial = serial.Serial(self.comm_port)
            self.connected = True
            self.reading = True
            print "Connected successfully to %s (%s)." % (self.comm_port, self.serial)
            thread.start_new_thread(self._read_line, (None, self.received_log, self))
            thread.start_new_thread(self._write_line, (None, self.queue))
            return True

        except Exception as e:
            print "Oh there was an exception loading the port %s" % self.comm_port
            print e.message
            self.connected = False
            self.serial = None
            return False

    def _read_line(self, freq, received_log, parent):

        while True:
            if self.reading:
                l = self.serial.readline().strip('\r\n')
                self.process_incoming_message(l, parent)
                received_log.append(l)
                if len(received_log) > 200:
                    received_log.popleft()
                print "%s: %s" % (self.name, l)
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
                        self.status = 'idle'
                    self.ready = False
                self.reading = True
            if freq:
                time.sleep(freq)




    def heartbeat(self, freq):
        """
        Setting status flags, and initiating new actions based on combinations of status flags.
        """
        print '%s Status: %s' % (self.name, self.status)
        while True:
            try:
                if self.status == 'idle':
                    if self.auto_acquire and self.can_acquire:
                        if self.layout.panels_left() > 0:
                            # acquire and use a new panel if successful
                            self.status = 'acquiring'
                        else:
                            # no panels left,
                            self.status = 'waiting_for_new_layout'

                elif self.status == 'acquiring':
                    try:
                        self.acquire()
                    except:
                        print "Exception occurred when attempting to acquire some artwork."


                elif self.status == 'acquired':
                    if not self.paths:
                        self.status = 'idle'
                        raise ValueError('Paths were not found, although status is acquired')

                    # find a new panel for this artwork
                    self.layout.remove_current_panel()
                    new_panel = self.layout.use_random_panel()
                    if not new_panel:
                        # No new panels! Need to wait for a whole new layout.
                        self.status = 'waiting_for_new_layout'
                        raise ValueError("There's a new panel")

                    # new panel is available, hooray
                    try:
                        self.paths = self.layout.scale_to_panel(self.paths)
                        commands = self.build_commands(self.paths)
                        print '%s Appending %s commands to the queue.' % (self.name, len(commands))
                        self.queue.extend(commands)
                        if self.queue:
                            self.status = 'serving'
                        else:
                            self.status = 'idle'

                    except ValueError:
                        self.paths = None
                        self.queue.clear()
                        self.layout.clear_panels()
                        self.status = 'waiting_for_new_layout'
                        raise

                elif self.status == 'waiting_for_new_layout':
                    self.queue_running = False

            except ValueError:
                pass

            if freq:
                time.sleep(freq)

    def get_machine_as_svg(self):
        filename = os.path.abspath("%s.svg" % self.name)
        paths2svg(self.paths or [],
                  self.extent.size, filename, scale=1.0, show_nodes=True, outline=True,
                  page=self.layout.extent, panel=self.layout.get_current_panel())

        return filename

    def get_available_panels_as_svg(self):
        filename = os.path.abspath("%s-layout.svg" % self.name)
        panel_paths = list()
        for p in self.layout.panels.values():
            path = list()
            path.append((p.position.x+6, p.position.y+6))
            path.append((p.position.x+p.size.x-12, p.position.y+6))
            path.append((p.position.x+p.size.x-12, p.position.y+p.size.y-12))
            path.append((p.position.x+6, p.position.y+p.size.y-12))
            path.append((p.position.x+6, p.position.y+6))
            panel_paths.append(path)

        paths2svg(panel_paths or [],
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

        result={'name': self.name,
                'status': self.status,
                'queue_running': self.queue_running,
                'calibrated': self.calibrated,
                'ready': self.ready,
                'last_move': self.last_move,
                'uptime': self.uptime(),
                'contacted': self.contacted,
                'page': self.current_page['name'],
                'camera_in_use': Polargraph.camera_lock,
                'current panel': str(self.layout.get_current_panel().__str__()),
                'layout design': str(self.layout.design),
                'comm port': self.comm_port,
        }
        if self.paths:
            result['paths'] = len(self.paths)
        else:
            result['paths'] = 0

        return result


    def control_acquire(self, command):
        if command == 'automatic':
            self.auto_acquire = True
        elif command == 'manual':
            self.status = 'idle'
            self.auto_acquire = False
        elif command == 'now':
            result = self.state()
            ac = self.acquire()
            if ac:
                result.update(ac)
            return result

        return self.state()

    def control_drawing(self, command):
        if command == 'run':
            if self.status == 'waiting_for_new_layout':
                self.set_layout(self.layout.extent, self.layout.design)
                self.status = 'idle'
            self.queue_running = True
        elif command == 'pause':
            self.queue_running = False
        elif command == 'cancel_panel':
            self.queue.clear()
            self.queue.append("C14,0,END")  # pen lift
            self.layout.remove_current_panel()
            self.status = 'idle'
        elif command == 'cancel_page':
            self.queue.clear()
            self.queue_running = False
            self.layout.clear_panels()
            self.queue.append("C14,0,END")  # pen lift
            self.status = 'waiting_for_new_layout'
        elif command == 'reuse_panel':
            self.queue.clear()
            self.layout.current_panel_key = None
            self.status = 'idle'

        return self.state()

    def control_pen(self, command):
        if command == 'up':
            self.queue.append(self.commands['pen_up'])
        elif command == 'down':
            self.queue.append(self.commands['pen_down'])

        return self.state()

    def control_movement(self, data):
        if 'speed' in data:
            self.queue.append("C31,%s,END" % data['speed'])
        if 'accel' in data:
            self.queue.append("C32,%s,END" % data['accel'])
        if 'calibrate' in data:
            self.queue.append("C48,END")

        return self.state()

    def draw_routine(self, routine_name):
        if routine_name == 'page_edge':
            p = self.layout.extent
            perimeter = [(p.position.x, p.position.y),
                (p.position.x+p.size.x, p.position.y),
                (p.position.x+p.size.x, p.position.y+p.size.y),
                (p.position.x, p.position.y+p.size.y),
                (p.position.x, p.position.y)]
            self.queue.extend(self.convert_paths_to_move_commands([perimeter]))

        elif routine_name == 'panel_edges':
            for p in self.layout.panels:
                self.queue.extend(self.convert_paths_to_move_commands([p]))

    def process_incoming_message(self, command, parent):
        """
        Receives messages from the machine and deals with them. This will involve:
        * raising errors
        * confirmations of updates
        * setting status
        """
        try:
            #print "Processing incoming message."
            if 'READY_300' in command:
                parent.contacted = True
                parent.ready = True
            elif 'CARTESIAN' in command:
                parent.calibrated = True
                parent.position = Polargraph.unpack_sync(command)
        except:
            pass

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

        p = self.layout.get_current_panel()
        perimeter = [(p.position.x, p.position.y),
                     (p.position.x+p.size.x, p.position.y),
            (p.position.x+p.size.x, p.position.y+p.size.y),
            (p.position.x, p.position.y+p.size.y),
            (p.position.x, p.position.y)]

        ps = [perimeter]
        ps.extend(paths)
        result = self.convert_paths_to_move_commands(ps)

        return result

    def convert_paths_to_move_commands(self, paths):
        result = []
        for path in paths:
            first = True
            for point in path:
                if first:
                    result.append(self.commands['pen_up'])
                    result.append("C17,%.0f,%.0f,8,END" % (point[0], point[1]))
                    result.append(self.commands['pen_down'])
                    first = False
                else:
                    result.append("C17,%.0f,%.0f,8,END" % (point[0], point[1]))

        result.append("C14,20,END")

        return result

