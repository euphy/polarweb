import cv2
import numpy as np


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