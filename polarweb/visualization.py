import cv2
import numpy as np


def shutter(frame):
    """ Return a black image.
    :return:
    """
    return np.zeros(frame.shape, np.uint8)

def captioned_image(frame, caption=''):
    """
    Returns the frame with a caption added.
    :param frame:
    :param caption:
    :return:
    """
    print "Caption: %s" % caption
    cv2.putText(frame,
                caption,
                (5, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255))
    return frame


def resize(step_input, initial_frame):
    return 