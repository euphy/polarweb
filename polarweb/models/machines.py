from collections import OrderedDict
import gevent
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

        # Unpack the MACHINES config settings into the
        for i in SETTINGS.MACHINES:
            print "Found named machine: %s" % i['name']
            print "%s has a spec: %s" % (i['name'], i['spec'])
            spec = i['spec']
            p = Polargraph(name=i['name'],
                           extent=spec['extent'],
                           page=SETTINGS.PAGES[spec['default_page']],
                           comm_port=spec['comm_port'],
                           baud_rate=spec['baud_rate'],
                           acquire_method=SETTINGS.ARTWORK_ACQUIRE_METHOD,
                           layout_name='2x2',
                           event_callback=outgoing_event_signaller,
                           viz=viz_thread)
            self[p.name] = p
            self.machine_names.append(p.name)
            gevent.sleep(1)
            p.machine_status_process.start()



    def list_ports(self):
        self.ports = list(list_ports.comports())
        print "Comm ports:"
        for p in self.ports:
            print p
        return self.ports