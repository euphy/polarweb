import base64
import copy
import io
import json
from threading import Thread
import traceback
from PIL import Image
import cv2
import gevent
import numpy as np
import time
from os import path
from polarweb.config import SETTINGS
from polarweb.image_grabber.lib.app import ImageGrabber
from gevent import Greenlet
import gevent
from polarweb.models.camera import Camera
from polarweb.models.framebuffer import FrameBuffer
from polarweb.models.layout import Layout


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
            b, g, r = cv2.split(f)

            img = Image.fromarray(cv2.merge([r, g, b]), 'RGB')
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
    c = copy.copy(frame)
    for line in caption:
        cv2.putText(c,
                    line,
                    (5, row),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (50, 50, 50), 5)
        cv2.putText(c,
                    line,
                    (5, row),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (255, 255, 255), 2)
        row += 32
    return c


def test_render_vector(paths=None):
    if not paths:
        # Get the json
        filename = path.join(path.split(path.dirname(path.abspath(__file__)))[0], 'drawing_planner', '20150325-223051.5640009816.json')
        j = json.loads(open(filename).read())
        paths = j['paths']

    # get the image
    bitmap = np.zeros([720,360,3], np.uint8)

    v = render_vector(bitmap, paths)
    return v

def render_vector(input, paths, show_travel=True, show_live=False):
    """
    Takes a bitmap, and a set of paths as parameters, and draws the vectors
    out onto the bitmap. Returns a copy of the input.

    :param initial_frame:
    :return:
    """
    out = copy.copy(input)

    paths = scale_paths(input.shape, paths)

    start_point = (0, 0)
    for path in paths:
        # draw travel lines
        to = (int(path[0][0]), int(path[0][1]))
        # print "From %s to %s" % (start_point, to)
        if show_travel:
            cv2.line(out, start_point, to, [0,100,100], 1)

        for i in range(1, len(path)):
            fr = (int(path[i-1][0]), int(path[i-1][1]))
            to = (int(path[i][0]), int(path[i][1]))
            # print "From %s to %s" % (fr, to)
            cv2.line(out, fr, to, [200,200,00], 2)

        start_point = (int(path[-1][0]), int(path[-1][1]))

    if show_live:
        cv2.imshow("output", out)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    return out

def scale_paths(panel_shape, paths):
    if not paths:
        return list()
    # Turn them into floats
    for path_index, path in enumerate(paths):
        for point_index, point in enumerate(path):
            paths[path_index][point_index] = (float(point[0]), float(point[1]))


    paths_shape = Layout.get_path_size(paths)
    print "Paths size: %s" % str(paths_shape)

    panel_ratio = panel_shape[0] / float(panel_shape[1])
    paths_ratio = paths_shape[1] / float(paths_shape[0])

    print "Panel ratio: %s" % panel_ratio
    print "Paths ratio: %s" % paths_ratio

    if panel_ratio > paths_ratio:
        scaling = panel_shape[1] / paths_shape[0]
    else:
        scaling = panel_shape[0] / paths_shape[1]

    print "Scaling: %s" % scaling
    for path_index, path in enumerate(paths):
        for point_index, point in enumerate(path):
            paths[path_index][point_index] = (point[0]*scaling, point[1]*scaling)

    return paths

def height_to_width(self):
    if self.size.x != 0.0:
        return self.size.y / self.size.x
    else:
        return 1.0

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
    last_frame = None

    for step in sequence:
        print "STEP: %s" % step
        if 'kwargs' in step:
            step_input = cv2.imread(img_filenames[step['filename_key']])
            h, w = initial_frame.shape[:2]
            step_input = cv2.resize(step_input, (w, h))
            if step['name'] is 'posterized':
                last_frame = copy.copy(step_input)
            step_frame = step['method'](step_input, **step['kwargs'])
        else:
            step_frame = step['method'](initial_frame)

        if viz is not None:
            viz.get_frame_buffer().write(step_frame)
            gevent.sleep(int(step['duration']))

    # Now display pathfinder stuff
    vector_process_wait = \
        captioned_image(last_frame,
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
            if SETTINGS.SHOW_PATHS_DURING_VIZ:
                new_paths = now.get('paths', None)
                if new_paths is not None and new_paths != last_now.get('paths', None):
                    last_frame = render_vector(shutter(last_frame), new_paths)

            vector_process_wait = \
                captioned_image(last_frame,
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
        captioned_image(last_frame,
                        caption=['Finished tracing...',
                                 'Now busy drawing!',
                                 '','','',
                                 '','','',
                                 '','','',
                                 '','','',
                                 '','',
                                 'Please wait for a',
                                 'machine to finish!'])
    viz.get_frame_buffer().write(vector_process_wait)

    # Get final paths
    prog, now = tracing_thread.get_progress()
    gevent.sleep(2)

    return now['paths']