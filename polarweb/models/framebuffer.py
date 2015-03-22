import io
import traceback
from PIL import Image
import gevent
import numpy as np

h = 640
w = 360
size = (h, w, 3)
frame = np.zeros(size)

class FrameBuffer():

    change = np.full(size, 1)
    last_retrieved = np.full(size, 255)

    def __init__(self):
        global frame
        self.frame = frame

    def write(self, frame):
        self.frame = frame
        gevent.sleep(0.001)

    def read(self):
        return self.frame
