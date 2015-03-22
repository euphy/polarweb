import base64
import copy
import io
from threading import Thread
import traceback
from PIL import Image
import cv2
import gevent
import numpy as np
import time
from polarweb.config import SETTINGS
from polarweb.image_grabber.lib.app import ImageGrabber
from gevent import Greenlet
import gevent
from polarweb.models.camera import Camera
from polarweb.models.framebuffer import FrameBuffer


class VisualizationThread(Greenlet):
    last_served = None

    def __init__(self):
        Greenlet.__init__(self)
        self.fb = FrameBuffer()
        self.camera = Camera()

    def read(self):
        # if self._streaming:
        #     try:
        #         print "From streaming"
        #         self.fb.write(self.camera.capture_frame())
        #     except IOError:
        #         # No new frame today, sir.
        #         pass
        frame = self.fb.read()
        return frame

    def read_jpeg_bytes(self, continuous=False):
        f = self.read()
        if not np.array_equal(self.last_served, f) or continuous:
            img = Image.fromarray(f, 'RGB')
            out_bytes = io.BytesIO()
            img.save(out_bytes, 'jpeg')
            self.last_served = f
            return out_bytes
        else:
            # print "No new frame!"
            return None

    def get_frame_buffer(self):
        return self.fb

def shutter(frame=None):
    """ Return a black image.
    :return:
    """
    return np.zeros(frame.shape, np.uint8)

def captioned_image(frame, caption=[]):
    """
    Returns the frame with a caption added.
    :param frame:
    :param caption: An array, each element will be presented on a new line.
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


def visualise_capture_process(img_filenames, tracing_thread, viz=None):
    for key in img_filenames:
        print "%s: %s" % (key, img_filenames[key])

    step_duration = 2
    sequence = [
        {'name': 'shutter',
         'duration': 0.5,
         'method': shutter},
        {'name': 'greyscaled',
         'duration': step_duration,
         'method': captioned_image,
         'kwargs': {'caption': ['Desaturated']},
         'filename_key': 'greyscale'},
        {'name': 'equalized',
         'duration': step_duration,
         'method': captioned_image,
         'kwargs': {'caption': ['Equalised']},
         'filename_key': 'equalized'},
        {'name': 'blurred',
         'duration': step_duration,
         'method': captioned_image,
         'kwargs': {'caption': ['Blurred']},
         'filename_key': 'blurred'},
        {'name': 'posterized',
         'duration': step_duration,
         'method': captioned_image,
         'kwargs': {'caption': ['Posterised']},
         'filename_key': 'posterized'},
        ]

    initial_frame = cv2.imread(img_filenames['raw'])
    for step in sequence:
        print "STEP: %s" % step
        if 'kwargs' in step:
            step_input = cv2.imread(img_filenames[step['filename_key']])
            h, w = initial_frame.shape[:2]
            step_input = cv2.resize(step_input, (w, h))
            step['kwargs']['caption']
            step_frame = step['method'](step_input, **step['kwargs'])
        else:
            step_frame = step['method'](initial_frame)

        if viz is not None:
            viz.get_frame_buffer().write(step_frame)
            gevent.sleep(int(step['duration']))

    # Now display vector stuff
    # Blank screen for a second
    vector_process_wait = \
        captioned_image(shutter(initial_frame),
                        caption=["Tracing image..."])
    viz.get_frame_buffer().write(vector_process_wait)
    gevent.sleep(1)

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

        viz.get_frame_buffer().write(vector_process_wait)
        gevent.sleep(0.2)

    tracing_thread.join()

    # Present some cleanup slides
    vector_process_wait = \
        captioned_image(shutter(initial_frame),
                        caption=['Finished tracing...'])
    viz.get_frame_buffer().write(vector_process_wait)
    gevent.sleep(4)

    vector_process_wait = \
        captioned_image(shutter(initial_frame),
                        caption=['Finished tracing...',
                                 '',
                                 '...'])
    viz.get_frame_buffer().write(vector_process_wait)
    gevent.sleep(4)

    vector_process_wait = \
        captioned_image(shutter(initial_frame),
                        caption=['Finished tracing...',
                                 '',
                                 '...',
                                 '',
                                 'Now drawing!'])
    viz.get_frame_buffer().write(vector_process_wait)
    gevent.sleep(4)

    prog, now = tracing_thread.get_progress()
    return now['paths']