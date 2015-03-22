from datetime import datetime, timedelta
import traceback
import cv2
import time
from polarweb.config import SETTINGS

__camera = None

def init_camera():
    global __camera
    if __camera is None:
        print "Initialising Camera."
        __camera = cv2.VideoCapture(SETTINGS.CAMERA_NUM)
    else:
        print "Camera already initialised."
    return __camera

def release_camera():
    global __camera
    if __camera is not None:
        __camera.release()

def transform_cam_frame(frame):
    """
    Utility function to transform a frame.
    :param frame:
    :return:
    """
    if SETTINGS.CAMERA_ORIENTATION == 'rotate cw':
        frame = cv2.transpose(frame)
        frame = cv2.flip(frame, 0)
    return frame

class Camera():
    min_frame_interval = timedelta(milliseconds=(1000 / 20))  # 20 fps
    last_capture_time = datetime.now()
    last_capture_frame = None

    def __init__(self, preloaded_image=None):
        if preloaded_image is None:
            self._camera = init_camera()
        else:
            self._camera = None
        self.preloaded_image = preloaded_image

    def release(self):
        release_camera()

    def get_camera(self):
        return self._camera

    def capture_frame(self, timeout=2.0):
        if self.preloaded_image is not None:
            return self.preloaded_image
        else:
            if (datetime.now() > (self.last_capture_time + self.min_frame_interval)):

                captured = False
                start_time = time.clock()
                while not captured:
                    captured, frame = self._camera.read()
                    if captured:
                        # print "captured"
                        self.last_capture_frame = transform_cam_frame(frame)
                    elif time.clock() > start_time + timeout:
                        raise IOError("Webcam did not respond in time (%s)"
                                      % timeout)
            else:
                print "already took a frame recently (%s, it's %s now)" % \
                (self.last_capture_time, datetime.now())

        return self.last_capture_frame


