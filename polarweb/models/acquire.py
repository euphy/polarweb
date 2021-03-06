from importlib import import_module
import cv2
from polarweb.config import SETTINGS
from polarweb.models import visualization
from polarweb.image_grabber.lib.app import ImageGrabber
from polarweb.pathfinder import workflow
import numpy as np
from polarweb.pathfinder.pathfinder_thread import PathfinderThread
import gevent

acquisition_lock = None

def get_acquire_func(method_name, module):
    """
    Function that returns a function, that in turn may be called and will
    acquire a piece of artwork.

    Alternatively it may return None, in which case there was no
    acquisition source configured.
    """
    mod = import_module(module)
    return getattr(mod, method_name)

def acquire_face_track(p, event_callback=None, viz=None):
    """
    Method that will acquire an image to draw.
    """
    print "%s In acquire face track" % p.name
    global acquisition_lock
    if not acquisition_lock:
        print "%s Setting ACQUISITION LOCK %s to True" % (p.name,
                                                          id(acquisition_lock))
        acquisition_lock = True
        event_callback(target='capture_status-%s' % p.name,
                       value="Acquiring...")
    else:
        print "Acquire function is locked. Cancelling. But do try again please!"
        p.status = 'idle'
        event_callback(target='capture_status-%s' % p.name,
                       value="Locked.")
        return {'http_code': 503}

    p.paths = list()

    # Initialise the face grabber
    min_face_size = SETTINGS.MIN_FACE_SIZE \
        if hasattr(SETTINGS, 'MIN_FACE_SIZE') else 150

    required_score = SETTINGS.FACE_LOCK_VALUE \
        if hasattr(SETTINGS, 'FACE_LOCK_VALUE') else 15

    print "Posterize levels: %s" % p.trace_settings['posterize_levels']

    grabber = ImageGrabber(debug=False,
                           required_score=required_score,
                           frame_buffer_func=viz.get_frame_buffer().write,
                           min_face_size=min_face_size,
                           posterize_levels=p.trace_settings['posterize_levels'],
                           blur=p.trace_settings['blur'])
    img_filenames = grabber.get_images(filename="png")
    event_callback(target='capture_status-%s' % p.name,
                   value='Got images.')

    tracing_thread = PathfinderThread(input_img=img_filenames['final'],
                                      min_path_length=p.trace_settings['min_path_length'],
                                      max_path_count=p.trace_settings['max_path_count'],
                                      smoothing_levels=p.trace_settings['path_smoothing_levels'],
                                      event_callback=event_callback)
    tracing_thread.start()

    image_paths = \
        visualization.visualise_capture_process(img_filenames,
                                                tracing_thread,
                                                viz)

    p.paths.extend(image_paths)
    if p.paths:
        p.status = 'acquired'
        event_callback(target='capture_status-%s' % p.name,
                       value='Paths captured.')
    else:
        print "That attempt to acquire didn't seem to result in any paths."
        p.status = 'idle'
        event_callback(target='capture_status-%s' % p.name,
                       value='Failed to produce paths.')

    print "%s RELEASING ACQUISITION LOCK %s" % (p.name,
                                                id(acquisition_lock))
    acquisition_lock = False


def acquire_dummy(p):
    """ Dummy acquisition function.
    """
    print "Attempted to call dummy acquire."
    return None