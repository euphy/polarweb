from serial.tools import list_ports
from polarweb.config import SETTINGS
from polarweb.models.polargraph import Polargraph

class Machines(dict):

    default_page = SETTINGS.PAGES[SETTINGS.DEFAULT_PAGE]
    default_page['name'] = SETTINGS.DEFAULT_PAGE

    def __init__(self, outgoing_event_signaller=None, viz_thread=None, *args, **kwargs):
        super(Machines, self).__init__(*args, **kwargs)
        self.__dict__ = self

        self.list_ports()
        self.machine_names = []
        for k, v in SETTINGS.MACHINES.items():
            p = Polargraph(name=k,
                           extent=v['extent'],
                           page=SETTINGS.PAGES[v['default_page']],
                           comm_port=v['comm_port'],
                           baud_rate=v['baud_rate'],
                           acquire_method=SETTINGS.ARTWORK_ACQUIRE_METHOD,
                           layout_name='2x2',
                           event_callback=outgoing_event_signaller,
                           viz=viz_thread)
            self[p.name] = p
            self.machine_names.append(p.name)
            p.machine_status_process.start()



    def list_ports(self):
        self.ports = list(list_ports.comports())
        print "Com ports: %s" % self.ports
        return self.ports

