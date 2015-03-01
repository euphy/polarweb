from importlib import import_module
import cv2
from polarweb.image_grabber.lib.app import ImageGrabber
from polarweb.pathfinder import workflow
import numpy as np


def get_acquire_func(method_name, module):
    """
    Function that returns a function, that in turn may be called and will
    acquire a piece of artwork.

    Alternatively it may return None, in which case there was no
    acquisition source configured.
    """
    mod = import_module(module)
    return getattr(mod, method_name)

def acquire_face_track(p):
    """
    Method that will acquire an image to draw.
    """
    if p.camera_lock:
        print "Camera is locked. Cancelling. But do try again please!"
        p.status = 'idle'
        return {'http_code': 503}

    p.camera_lock = True
    p.paths = list()

    grabber = ImageGrabber(debug=False, visualise_capture=True)
    img_filenames = grabber.get_images(filename="png")
    print "Got images: %s" % img_filenames

    image_paths = workflow.run(input_img=img_filenames['final'])
    p.paths.extend(image_paths)
    if p.paths:
        p.status = 'acquired'
    else:
        print "That attempt to acquire didn't seem to result in any paths."
        p.status = 'idle'
    p.camera_lock = False

def show_visualization_window():
    cv2.imshow('visual', np.zeros((640, 360, 3)))

def acquire_dummy(p):
    """ Dummy acquisition function.
    """
    print "Attempted to call dummy acquire."
    return None