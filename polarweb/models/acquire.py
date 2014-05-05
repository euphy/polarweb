from importlib import import_module
from polarweb.image_grabber.lib.app import ImageGrabber
from polarweb.pathfinder import sample_workflow


def get_acquire_func(method_name, module):
    """
    Function that returns a function, that in turn may be called and will acquire a piece of artwork.

    Alternatively it may return None, in which case there was no acquisition source configured.
    """
    mod = import_module(module)
    return getattr(mod, method_name)

def acquire_face_track(p):
    """  Method that will acquire an image to draw.
    """
    if p.camera_lock:
        print "Camera is locked. Cancelling. But do try again please!"
        p.status = 'idle'
        return {'http_code': 503}

    p.camera_lock = True
    p.paths = list()

    grabber = ImageGrabber(debug=True)
    img_filename = grabber.get_image(filename="png", rgb_ind=p.rgb_ind)
    print "Got %s" % img_filename

    p.paths.extend(sample_workflow.run(input_img=img_filename, rgb_ind=p.rgb_ind))
    if p.paths:
        p.status = 'acquired'
    else:
        print "That attempt to acquire didn't seem to result in any paths."
        p.status = 'idle'
    p.camera_lock = False

def acquire_dummy(p):
    """ Dummy acquisition function.
    """
    print "Attempted to call dummy acquire."
    return None