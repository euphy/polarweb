import base64
import copy
import io
from threading import Thread
from PIL import Image
import cv2
import gevent
import numpy as np
import time
from polarweb.image_grabber.lib.app import ImageGrabber
from gevent import Greenlet

class VisualizationThread(Greenlet):
    h = 640
    w = 360

    frame = np.zeros((640, 360, 3))
    change = np.full((640, 360, 3), 1)
    last_served = np.full((640, 360, 3), 255)
    camera = None

    def __init__(self, name='visual'):
        Greenlet.__init__(self)
        # Thread.__init__(self, name="visualization")
        self.window_name = name
        # self.grabber = ImageGrabber(debug=False)
        print "On it."

    def imshow(self, frame):
        # print "accepting frame (%s)" % frame[0:1][0][0][0]
        self.frame = frame
        gevent.sleep(0.001)

    def get_frame(self):
        # self.frame = self.grabber.get_frame()
        # print "Emitting frame %s (%s)" % (self, self.frame[0:1][0][0][0])
        # gevent.sleep(0)
        return self.frame

    def get_jpeg_bytes(self, continuous=False):
        f = self.get_frame()
        if not np.array_equal(self.last_served, f) or continuous:
            img = Image.fromarray(f, 'RGB')
            out_bytes = io.BytesIO()
            img.save(out_bytes, 'jpeg')
            self.last_served = f
            return out_bytes
        else:
            # print "No new frame!"
            return None

    def run(self):
        while True:
            pass

    def window(self, show):
        if show:
            cv2.namedWindow('visual')
        else:
            cv2.destroyWindow('visual')

def shutter(frame):
    """ Return a black image.
    :return:
    """
    return np.zeros(frame.shape, np.uint8)

def captioned_image(frame, caption=[]):
    """
    Returns the frame with a caption added.
    :param frame:
    :param caption:
    :return:
    """
    # print "Caption: %s" % caption
    row = 30
    for line in caption:
        cv2.putText(frame,
                    line,
                    (5, row),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (255, 255, 255))
        row += 32
    return frame


def resize(step_input, initial_frame):
    return


def visualise_capture_process(img_filenames, tracing_thread):
    for key in img_filenames:
        print "%s: %s" % (key, img_filenames[key])

    sequence = [
        {'name': 'shutter',
         'duration': 0.5,
         'method': shutter},
        {'name': 'greyscaled',
         'duration': 2,
         'method': captioned_image,
         'kwargs': {'caption': ['Desaturated']},
         'filename_key': 'greyscale'},
        {'name': 'equalized',
         'duration': 2,
         'method': captioned_image,
         'kwargs': {'caption': ['Equalised']},
         'filename_key': 'equalized'},
        {'name': 'blurred',
         'duration': 2,
         'method': captioned_image,
         'kwargs': {'caption': ['Blurred']},
         'filename_key': 'blurred'},
        {'name': 'posterized',
         'duration': 2,
         'method': captioned_image,
         'kwargs': {'caption': ['Posterised']},
         'filename_key': 'posterized'},
        ]

    initial_frame = cv2.imread(img_filenames['raw'])
    for step in sequence:
        print step
        print "hello!"
        if 'kwargs' in step:
            step_input = cv2.imread(img_filenames[step['filename_key']])
            h, w = initial_frame.shape[:2]
            step_input = cv2.resize(step_input, (w, h))
            step['kwargs']['caption']
            step_frame = step['method'](step_input, **step['kwargs'])
        else:
            step_frame = step['method'](initial_frame)

        cv2.imshow('visual', step_frame)
        cv2.waitKey(int(step['duration']*1000))
        print "waited %s" % int(step['duration']*1000)

    # Now display vector stuff
    # Blank screen for a second
    vector_process_wait = \
        captioned_image(shutter(initial_frame),
                        caption=["Tracing image..."])
    cv2.imshow('visual', vector_process_wait)
    cv2.waitKey(1000)

    # Update blank screen with progress reports as long as the thread runs
    last_now = {'name': None,
                'status': None}
    while tracing_thread.is_alive():
        prog, now = tracing_thread.get_progress()

        # rebuild the frame if something has changed
        if now['status'] != last_now['status']:
            vector_process_wait = \
                captioned_image(shutter(initial_frame),
                                caption=["Tracing image...",
                                         now['name'],
                                         now['status']])
            last_now = copy.copy(now)
        else:
            # print "Not changed: %s" % now
            # print "(Last: %s)" % last_now
            pass

        cv2.imshow('visual', vector_process_wait)
        cv2.waitKey(100)

    tracing_thread.join()
    prog, now = tracing_thread.get_progress()
    cv2.destroyWindow('visual')
    return now['paths']