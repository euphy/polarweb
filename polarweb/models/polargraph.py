"""
General model of the machine, including its communications route.
"""
from collections import deque
from datetime import datetime
import multiprocessing
import os
import random
import string
import threading
import time
import thread
import traceback
import gevent

import serial
from euclid import Vector2
from polarweb import visualization

from polarweb.models import acquire
from polarweb.pathfinder import paths2svg
from polarweb.models.geometry import Rectangle, Layout

def update_machine_status(freq, p, viz):
    while True:
        p.update_status(viz)
        if freq:
            time.sleep(freq)

def event_monitor(freq, p):
    while True:
        p.send_events(p.event_callback)
        if freq:
            time.sleep(freq)

camera_lock = False

class Polargraph():
    """
    This is a model of a drawing machine. It includes it's drawing state
    as well as the state of the communications lines to the machine and the
    queue of commands going to it.

    Each machines has a:

    * name
    * extent (size and position of machine)
    * page (size of paper)
    * communication port
    * method of acquiring some artwork to draw
    * drawing layout that splits the page

    """

    last_seen = dict()

    def __init__(self,
                 name, extent, page,
                 comm_port=None,
                 baud_rate=9600,
                 acquire_method=None,
                 layout_name='3x3',
                 event_callback=None,
                 viz=None):

        global camera_lock
        print "Camera lock: %s" % id(camera_lock)
        self.camera_lock = camera_lock

        self.name = name
        self.extent = extent
        self.current_page = page
        self.comm_port = comm_port
        self.baud_rate = baud_rate

        # Physical machine state model
        self.connected = False
        self.contacted = False
        self.calibrated = False
        self.ready = False
        self.page_started = False

        self.serial = None
        self.queue = deque(['C17,400,400,10,END'])
        self.received_log = deque()
        self.reading = False

        self.wait_for_new_layout()
        self.set_layout(page['extent'], layout_name)

        self.last_move = None
        self.started_time = datetime.now()

        # internal states
        self.auto_acquire = True
        self.drawing = False
        self.queue_running = True
        self.position = None

        self.paths = None
        self.viz = viz
        self.streaming = False

        # set up acquire strategy
        self.can_acquire = False
        if acquire_method:
            try:
                self.acquire = \
                    acquire.get_acquire_func(acquire_method['method_name'],
                                             acquire_method['module'])
                self.can_acquire = True
            except:
                self.can_acquire = False

        # Init the serial io
        self.start_serial_comms()

        # and the event update_status
        self.machine_status_process = threading.Thread(target=update_machine_status,
                                           args=(random.uniform(0.5, 1.1), self, viz),
                                           name="update_machine_%s" % id(self))
        if event_callback is not None:
            self.event_callback = event_callback
            event_monitor_process = threading.Thread(target=event_monitor,
                                                     args=(2, self),
                                                     name='event_monitor')
            event_monitor_process.start()
        else:
            self.event_callback = None

        self.commands = {'pen_up': 'C14,20,END',
                         'pen_down': 'C13,130,END'}

        print "Initialised: %s." % self

    monitor = ('name',
               'status',
               'queue_running',
               'calibrated',
               'ready',
               'last_move',
               'contacted',
               'page',
               'camera_in_use',
               'current panel',
               'layout design',
               'comm port')

    def send_events(self, callback):
        # print "starting event monitor thread"
        updated = list()
        # 1. Look for changed elements
        for name in self.monitor:
            try:
                current = getattr(self, name)
                if name not in self.last_seen \
                        or self.last_seen[name] != current:
                    self.last_seen[name] = current
                    updated.append({'target': '%s-%s' % (name, self.name),
                                    'value': current})
            except AttributeError:
                continue

        updated.append({'target': 'uptime-%s' % self.name,
                        'value': '%s:%s:%s' % self.uptime()})

        # 2. Run callback on each one
        for each in updated:
            callback(each)



    def start_serial_comms(self):
        """
        Attempts to connect this machine to it's comm_port. It starts two
        threads, one for reading that is attached to the 'received_log'
        list, and one thread for writing that is attached to the main outgoing
        command queue.

        :return:
        """
        try:
            self.serial = serial.Serial(self.comm_port,
                                        baudrate=self.baud_rate)
            self.connected = True
            self.reading = True
            print "Connected successfully to %s (%s)." % (self.comm_port,
                                                          self.serial)
            thread.start_new_thread(self._read_line, (None,
                                                      self.received_log))
            thread.start_new_thread(self._write_line, (None,
                                                       self.queue))
            return True

        except Exception as e:
            print("Oh there was an exception loading the port %s"
                  % self.comm_port)
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
                    c = outgoing_queue.popleft()
                    self.serial.write(c+"\n")
                    print "Writing out: %s" % c
                    self.ready = False
                # else:
                #     self.status = 'idle'
                self.reading = True
            if freq:
                time.sleep(freq)

    def update_status(self, viz=None):
        """
        Transitions the machine status when NOT driven by external
        events.

        This is an implementation of a finite state machine, it runs in a
        thread, and controls the "automatic" behaviour of the machine, how it
        behaves when, for instance, the queue empties and there's no lines
        left to dispatch.

        It's designed to be called repeatedly.

        """

        print "CAmera lock: %s" % id(camera_lock)
        try:
            if self.status == 'idle':
                if self.auto_acquire and self.can_acquire:
                    if self.layout.panels_left() > 0:
                        # acquire and use a new panel if successful
                        self.status = 'acquiring'
                    else:
                        # no panels left,
                        print "No panels left!"
                        self.wait_for_new_layout()

            elif self.status == 'acquiring':
                try:
                    print "self.status == 'acquiring'"
                    print "CAMMERA LOCK!! %s" % id(self.camera_lock)
                    if self.camera_lock:
                        print "Camera is locked."
                    else:
                        self.acquire(self, self.event_callback, viz=viz)

                except Exception as e:
                    print traceback.format_exc(e)
                    print "Exception occurred when attempting to " \
                          "acquire some artwork %s" % e.message
                finally:
                    self.camera_lock = False

            elif self.status == 'acquired':
                self.viz.imshow(
                    visualization.captioned_image(
                        visualization.shutter(self.viz.get_frame()),
                        caption=['', '', '', "Now", 'drawing!']))
                if not self.paths:
                    self.status = 'idle'
                    raise ValueError('Paths were not found, '
                                     'although status is acquired')

                # find a new panel for this artwork
                self.layout.remove_current_panel()
                new_panel = self.layout.use_random_panel()
                if not new_panel:
                    # No new panels! Need to wait for a whole new layout.
                    self.wait_for_new_layout()
                    raise ValueError("There's a new panel")

                # new panel is available, hooray
                try:
                    self.paths = self.layout.scale_to_panel(self.paths)
                    commands = self.build_commands(self.paths)
                    print ('%s Appending %s commands to the queue.'
                           % (self.name, len(commands)))
                    self.queue.extend(commands)
                    if self.queue:
                        self.status = 'serving'
                    else:
                        self.status = 'idle'

                except ValueError as ve:
                    print ve
                    self.paths = None
                    self.queue.clear()
                    self.layout.clear_panels()
                    self.wait_for_new_layout()
                    raise

            elif self.status == 'waiting_for_new_layout':
                print "in %s" % self.status

        except ValueError:
            pass

    def get_machine_as_svg(self):
        filename = os.path.abspath("%s.svg" % self.name)
        paths2svg(self.paths or [],
                  self.extent.size, filename, scale=1.0, show_nodes=True,
                  outline=True,
                  page=self.layout.extent,
                  panel=self.layout.get_current_panel()
        )

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
                  self.extent.size, filename, scale=1.0, show_nodes=True,
                  outline=True,
                  page=self.layout.extent,
                  panel=self.layout.get_current_panel()
        )

        return filename

    def uptime(self):
        """
        Returns the time since starting.
        """
        d = datetime.now() - self.started_time
        s = d.seconds
        hours, remainder = divmod(s, 3600)
        minutes, seconds = divmod(remainder, 60)
        return hours, minutes, seconds

    def state(self):
        """
        Returns a dict of info about the state of the machine.
        :return:
        """

        result = {'name': self.name,
                  'status': self.status,
                  'queue_running': self.queue_running,
                  'calibrated': self.calibrated,
                  'ready': self.ready,
                  'last_move': self.last_move,
                  'uptime': self.uptime(),
                  'contacted': self.contacted,
                  'page': self.current_page['name'],
                  'camera_in_use': Polargraph.camera_lock,
                  'current panel': str(self.layout.get_current_panel()
                                       .__str__()),
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
            print "setting to idle 7"
            self.status = 'idle'
            self.auto_acquire = False
        elif command == 'now':
            self.status = 'acquiring'
        return self.state()

    def control_drawing(self, command):
        if command == 'run':
            if self.status == 'waiting_for_new_layout':
                print "Changing status from waiting_for_new_layout to idle"
                self.set_layout(self.layout.extent, self.layout.design)
                self.status = 'idle'
            self.queue_running = True
        elif command == 'pause':
            self.queue_running = False
        elif command == 'cancel_panel':
            self.queue.clear()
            self.queue.append(self.commands['pen_up'])  # pen lift
            self.layout.remove_current_panel()
            self.status = 'idle'
        elif command == 'cancel_page':
            self.queue.clear()
            self.queue.append(self.commands['pen_up'])  # pen lift
            self.layout.clear_panels()
            self.wait_for_new_layout()
        elif command == 'reuse_panel':
            self.queue.clear()
            self.layout.current_panel_key = None
            print "setting to idle 4"
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

    def control_machine(self, data):
        if 'restart' in data:
            self.queue.clear()
            self.queue_running = True
            self.queue.append('C51,END')

        return self.state()

    def draw_routine(self, routine_name):
        """
        Adds commands to the queue for various pre-baked routines, currently:

            'page_edge':   perimeter of defined page space
            'panel_edges': the perimeters of the layout panels

        :param routine_name:
        :return:
        """
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

    def process_incoming_message(self, command):
        """
        Receives messages from the machine and deals with them.
        This involves:

        * raising errors
        * confirmations of updates
        * setting status
        """
        try:
            #print "Processing incoming message."
            if 'READY' in command:
                self.contacted = True
                self.ready = True
            elif 'CARTESIAN' in command:
                self.calibrated = True
                self.position = Polargraph.unpack_sync(command)
            elif 'BUTTON' in command:
                print "Button pressed"
                self.control_drawing('run')
        except:
            pass

    @classmethod
    def unpack_sync(cls, command):
        splitted = command.split(",")
        return Vector2(splitted[1], splitted[2])

    def set_layout(self, page, layout_name):
        """
        If the machine is waiting for a new layout, it creates a new one, and
        selects a new panel to target.

        :param page:
        :param layout_name:
        :return:
        """
        if self.status == 'waiting_for_new_layout':
            self.layout = Layout(page, layout_name)
            self.layout.use_random_panel()
            self.status = 'idle'
            self.queue.append('C50,END')

        return {'layout': layout_name,
                'page': page}


    def build_commands(self, paths):
        """
        Takes a list of paths, corresponding to one panels-worth of drawing,
        and returns a list of string commands.

        :param paths:
        :return:
        """

        p = self.layout.get_current_panel()
        perimeter = \
            [(p.position.x, p.position.y),
             (p.position.x+p.size.x, p.position.y),
             (p.position.x+p.size.x, p.position.y+p.size.y),
             (p.position.x, p.position.y+p.size.y),
             (p.position.x, p.position.y)]

        ps = [perimeter]
        ps.extend(paths)
        result = self.convert_paths_to_move_commands(ps)

        return result

    def convert_paths_to_move_commands(self, paths):
        """
        Unpacks a list of paths, which are themselves a list of points.
        Adds a pen-up and pen-down at the beginning of each path,
        and a pen-up at the end.

        :param paths:
        :return:
        """
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

        result.append(self.commands['pen_up'])

        return result

    def wait_for_new_layout(self):
        self.queue.append('C49,END')
        self.status = 'waiting_for_new_layout'

