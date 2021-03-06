from datetime import datetime
import time

import os
from random import randint

import cv2
from PIL import Image
import gevent
import numpy as np
from polarweb.config import SETTINGS
from polarweb.image_grabber.lib.face import Tracking, Framing
import image as face_image

import gevent
from polarweb.models.camera import Camera


class ImageGrabber(object):
    width = None
    height = None
    frame = None
    gray = None
    faces = None
    last_highest = 0
    viz = None
    min_face_size = 200

    def dummy_frame_buffer(self, frame):
        print "Using dummy frame buffer."
        pass

    def __init__(self,
                 debug=False, required_score=15, blur=6,
                 posterize_levels=3, threshold_zoom=0.9,
                 input_image_filename=None,
                 visualise_capture=True,
                 camera=None,
                 frame_buffer_func=None,
                 min_face_size=200):

        self.debug = debug
        self.blur = blur
        self.posterize_levels = posterize_levels
        self.threshold_zoom = threshold_zoom
        self.visualise_capture = visualise_capture
        self.min_face_size = min_face_size

        path = os.path.split(__file__)[0]
        self.face_cascade = cv2.CascadeClassifier(
            os.path.join(path,
                         '../resource/haarcascade_frontalface_default.xml'))

        self.camera = camera if camera is not None else Camera()

        divider = 3
        self.set_resolution(1920/divider, 1080/divider)
        self.tracking = Tracking()
        self.tracking.score_max = required_score
        if frame_buffer_func is not None:
            self.frame_buffer_write = frame_buffer_func
        else:
            self.frame_buffer_write = self.dummy_frame_buffer

        try:
            if input_image_filename:
                img = Image.open(input_image_filename)
                img.thumbnail((max((self.width, self.height)), max((self.width, self.height))), Image.ANTIALIAS)
                self.preloaded_image = np.array(img)
            else:
                self.preloaded_image = None
        except Exception as e:
            print e
            print "Input image (%s) was not loaded." % input_image_filename
            pass

    def set_resolution(self, x, y):
        self.width = x
        self.height = y

        self.camera.get_camera().set(3, x)
        self.camera.get_camera().set(4, y)

    def posterize_image(self, img):
        thresholds = face_image.get_threshold_boundaries(
            img, self.posterize_levels)
        img = face_image.threshold(img, thresholds)
        return img

    def blur_image(self, img):
        proportionate_blur = int((img.shape[1] / (self.blur*10)+0.5))
        print "Blur level: %s" % proportionate_blur
        return cv2.blur(img, ksize=(proportionate_blur, proportionate_blur))

    def process_image(self, img):
        filenames = dict()

        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        filenames['greyscale'] = self.save_image_as_file(img, 'png')

        img = cv2.equalizeHist(img)
        filenames['equalized'] = self.save_image_as_file(img, 'png')

        img = self.blur_image(img)
        filenames['blurred'] = self.save_image_as_file(img, 'png')

        img = self.posterize_image(img)
        filenames['posterized'] = self.save_image_as_file(img, 'png')
        filenames['final'] = filenames['posterized']

        return img, filenames


    def get_image(self, filename="png"):
        self.last_highest = 0
        if self.debug:
            print "Obtaining face lock..."

        self._wait_for_face_lock()

        if self.debug:
            print "Face lock obtained"

        filenames = dict()
        if filename:
            filenames['raw'] = self.save_image_as_file(self.frame, filename)

        _, _, portrait_rect = self._isolate_face()
        crop = face_image.sub_image(self.frame, portrait_rect)

        # Blur and dynamically threshold it
        img, fnames = self.process_image(crop)
        filenames.update(fnames)
        filenames['final'] = self.save_image_as_file(img, filename)
        return img, filenames

    def get_images(self, filename=None):
        im, fnames = self.get_image(filename=filename)
        return fnames

    def save_image_as_file(self, image_array, filename):
        """
        If filename has no extension, then it is used as the extension.
        Eg filename == 'png' then, a default filename is generated, with a png extension.
        """
        im = Image.fromarray(image_array)

        _, ext = os.path.splitext(filename)
        if not ext:
            ext = filename
            filename = None

        if filename:
            full_file_path = os.path.abspath(filename)
        else:
            full_file_path = os.path.abspath("../pics/%s/%s%d.%s"
                                             % (datetime.now().strftime("%Y%m%d"),
                                                datetime.now().strftime("%Y%m%d-%H%M%S.%f"),
                                                randint(1000, 9999),
                                                ext))

        path, fname = os.path.split(full_file_path)

        if path and not os.path.exists(path):
            os.makedirs(path)

        print "Saving to %s" % full_file_path
        im.save(full_file_path)
        return full_file_path

    def close(self):
        self.camera.release()
        cv2.destroyAllWindows()

    #------------------#------------------------------------------------------#
    # Internal Methods #
    #------------------#

    def _isolate_face(self):
        # Find the biggest face
        faces = self.tracking.faces_by_size()
        if not faces:
            return
        biggest_face_id = faces[0][0]

        face_rect = self.tracking.face_boundary(biggest_face_id)

        # Get a tight image around the face
        framing = Framing(self.gray)
        frame_rect = framing.tighten_rect(face_rect, self.threshold_zoom)

        # Get a framed image about the face
        portrait_rect = framing.single_portrait(face_rect)

        return face_rect, \
               frame_rect, \
               portrait_rect

    def _capture_frame(self):
        # print "_capture_Frame in ImageGrabber"
        self.frame = self.camera.capture_frame()

        self.gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        # self.gray = cv2.equalizeHist(self.gray)
        self.faces = self.face_cascade.detectMultiScale(self.gray, 1.3, 5)

        # Filter out small faces
        self.big_faces = [f for f in self.faces if f[2] >= self.min_face_size]

        if len(self.big_faces) != len(self.faces):
            # Come closer, my pretty...
            pass

        self.tracking.observe(self.big_faces)

        return self.frame

    def _wait_for_face_lock(self):
        while True:
            if (not hasattr(self, 'faces')
                or self.faces == None
                or len(self.faces) == 0):
                self.last_highest = 0
            else:
                diff = self.tracking.score_max - self.last_highest
                if self.debug:
                    print "Diff: %s" % diff
                diff = diff / 20.0
            self._capture_frame()

            # Is a lock obtained?
            if self._face_lock_obtained():
                return

            if self.visualise_capture:

                highlighted = np.copy(self.frame)
                self.tracking.highlight_faces(highlighted,
                                              scale=1,
                                              all_faces=self.faces,
                                              big_faces=self.big_faces)
                self.frame_buffer_write(highlighted)

                # cv2.imshow('visual', highlighted)
                if self.debug:
                    for face in self.faces:
                        (x, y, w, h) = face
                        cv2.rectangle(highlighted,
                                      (x, y),
                                      (x + w, y + h),
                                      (255, 0, 255), 2)

                    try:
                        face_rect, avg, portrait = self._isolate_face()
                        cv2.rectangle(highlighted,
                                      (int(avg[0]), int(avg[1])),
                                      (int(avg[0]+avg[2]),
                                       int(avg[1]+avg[3])),
                                      (200, 200, 0),
                                      2)
                        cv2.rectangle(highlighted,
                                      (int(portrait[0]), int(portrait[1])),
                                      (int(portrait[0]+portrait[2]),
                                       int(portrait[1]+portrait[3])),
                                      (255, 255, 0),
                                      2)
                    except TypeError as te:
                        print te.message
                        print "ah! There was no face to be found!"

                    equalized = cv2.cvtColor(self.gray,
                                             cv2.COLOR_GRAY2BGR)
                    blurred = self.blur_image(equalized)
                    posterized = self.posterize_image(blurred)

                    # make a composite version
                    height, width, depth = self.frame.shape
                    comp = np.zeros((height,
                                     width*4,
                                     depth),
                                    np.uint8)

                    comp[:height, :width] = highlighted
                    comp[:height, width:width*2] = equalized
                    comp[:height, width*2:width*3] = blurred
                    comp[:height, width*3:width*4] = posterized

                    cv2.imshow('comp', comp)

            if cv2.waitKey(20) & 0xFF == ord('q'):
                self.close()
                raise Exception('User requested quit')

    def _face_lock_obtained(self):
        for face in self.tracking.evidence.values():
            self.last_highest = face['score'] if face['score'] > self.last_highest else self.last_highest
            if face['score'] == self.tracking.score_max:
                return True
        return False