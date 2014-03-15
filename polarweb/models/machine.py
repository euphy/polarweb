"""
General model of the machine, including its communications route.
"""
from datetime import datetime
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
                              'page_extent':Rectangle(Vector2(210, 297), Vector2(55, 60))},
                        comm_port="COM18")
        m2 = Polargraph("right", Rectangle(Vector2(305, 450), Vector2(0, 0)),
                        page={'name': 'A4',
                              'page_extent':Rectangle(Vector2(210, 297), Vector2(55, 60))},
                        comm_port="COM22")

        self[m1.name] = m1
        self[m2.name] = m2
        self.machine_names = [m1.name, m2.name]
        self.ports = list(list_ports.comports())


class Polargraph():

    DT_FORMAT = "%y-%m-%dT%H:%M:%S.%f"
    def __init__(self, name, extent, page, comm_port=None):
        self.name = name
        self.extent = extent
        self.current_page = page

        self.comms_queue = CommandQueue(comm_port)
        self.calibrated = False
        self.ready = False
        self.page_started = False

        self.last_move = datetime.now()
        self.contacted = datetime.now()
        self.started_time = datetime.now()
        self.set_layout('1off')

        self.acquiring = False
        self.drawing = False


    def uptime(self):
        d = datetime.now() - self.started_time
        s = d.seconds
        hours, remainder = divmod(s, 3600)
        minutes, seconds = divmod(remainder, 60)
        return '%s:%s:%s' % (hours, minutes, seconds)

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
        if command == 'start':
            self.acquiring = True
        if command == 'pause':
            self.acquiring = False

class CommandQueue():

    def __init__(self, comm_port):
        self.comm_port = comm_port
        queue = []

