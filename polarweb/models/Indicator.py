from threading import Thread
import time

import webcolors
from arduino.usbdevice import ArduinoUsbDevice

class AcquireIndicator():
    """
        http://learn.adafruit.com/hacking-the-kinect/installing-python-and-pyusb
        https://github.com/digistump/DigisparkExamplePrograms/tree/master/Python/DigiBlink

        Copy Arduino python package (from DigisparkExamplePrograms) into site-packages.
        Install pyusb via pip or setup.py install.
    """
    def __init__(self):
        try:
            self.digispark = ArduinoUsbDevice(idVendor=0x16c0, idProduct=0x05df)

            print "Found: 0x%04x 0x%04x %s %s" % (self.digispark.idVendor,
                                                  self.digispark.idProduct,
                                                  self.digispark.productName,
                                                  self.digispark.manufacturer)
            self.set_colour(name='silver')
            time.sleep(1)
            self.set_colour(name='yellow')
            time.sleep(1)
            self.set_colour(name='fuchsia')
            time.sleep(1)
            self.set_colour(name='black')

        except:
            self.digispark = None

    def set_colour(self, name=None, val=None):
        if not self.digispark:
            return None

        if name:
            color_list = webcolors.name_to_rgb(name.lower())
            color_list = list(color_list)
        elif val:
            color_list = val
        else:
            raise

        self.digispark.write(ord("s"))

        if color_list[0] == 0:
            self.digispark.write(0)
        else:
            self.digispark.write(int(color_list[0]))

        if color_list[1] == 0:
            self.digispark.write(0)
        else:
            self.digispark.write(int(color_list[1]))

        if color_list[2] == 0:
            self.digispark.write(0)
        else:
            self.digispark.write(int(color_list[2]))

    def off(self):
        self.set_colour(name='black')

class FlashColourThread(Thread):
    def __init__(self, rgb_ind, on_col, on_for, off_col=None, off_for=None, num_of_flashes=-1):
        Thread.__init__(self)
        self.rgb_ind = rgb_ind,
        self.on_col = on_col
        self.on_for = on_for
        self.off_col = off_col or 'black'
        self.off_for = off_for or on_for

        self.exiting = False
        self.flashes_to_go = 0 -num_of_flashes

    def run(self):
        while not self.exiting:
            if isinstance(self.on_col, basestring):
                kw = {'name': self.on_col}
            else:
                kw = {'val': self.on_col}

            self.rgb_ind[0].set_colour(**kw)
            time.sleep(self.on_for)

            if isinstance(self.off_col, basestring):
                kw = {'name': self.off_col}
            else:
                kw = {'val': self.off_col}
            self.rgb_ind[0].set_colour(**kw)
            time.sleep(self.off_for)
            self.flashes_to_go += 1
            if self.flashes_to_go == 0:
                self.exiting = True

        else:
            self.rgb_ind[0].off()

    def change_pattern(self, on_col, on_for, off_col=None, off_for=None, num_of_flashes=-1):
        self.on_col = on_col
        self.on_for = on_for
        self.off_col = off_col or 'black'
        self.off_for = off_for or on_for

        self.exiting = False
        self.flashes_to_go = 0 -num_of_flashes

    def stop(self):
        self.rgb_ind[0].off()
        self.exiting = True


