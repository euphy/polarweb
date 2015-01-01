from datetime import datetime
import os
from random import randint

import cv2
from PIL import Image
from polarweb.image_grabber.lib.face import Tracking, Framing
import image as face_image


class ImageGrabber(object):
    width = None
    height = None
    frame = None
    gray = None
    faces = None
    last_highest = 0

    def __init__(self,
                 debug=False, required_score=15, blur=2,
                 posterize_levels=3, threshold_zoom=0.9, input_image=None):

        self.debug = debug
        self.blur = blur
        self.posterize_levels = posterize_levels
        self.threshold_zoom = threshold_zoom

        path = os.path.split(__file__)[0]
        self.face_cascade = cv2.CascadeClassifier(
            os.path.join(path, '../resource/haarcascade_frontalface_default.xml'))

        self.camera = cv2.VideoCapture(1)
        self.set_resolution(640, 480)

        self.tracking = Tracking()
        self.tracking.score_max = required_score

        try:
            if input_image:
                self.preloaded_image = Image.open(input_image)
        except:
            print "Input image (%s) was not loaded." % input_image
            pass

    def set_resolution(self, x, y):
        self.width = x
        self.height = y

        self.camera.set(3, x)
        self.camera.set(4, y)

    def process_image(self, img):
        # Blur and dynamically threshold it
        img = cv2.blur(img, ksize=(self.blur, self.blur))
        thresholds = face_image.get_threshold_boundaries(
            img, self.posterize_levels)
        img = face_image.threshold(img, thresholds)

        return img

    def get_image(self, filename=None, rgb_ind=None):
        self.last_highest = 0
        indicator_thread = None
        if rgb_ind:
            # indicator_thread = FlashColourThread(rgb_ind, 'orange', 0.2, 'black', 2)
            indicator_thread.start()

        if self.debug:
            print "Obtaining face lock..."

        self._wait_for_face_lock(indicator_thread=indicator_thread)
        if indicator_thread:
            indicator_thread.stop()

        if self.debug:
            print "Face lock obtained"

        if filename:
            self.save_image_as_file(self.frame, filename)

        if rgb_ind:
            indicator_thread = FlashColourThread(rgb_ind, 'green', 4, num_of_flashes=1)
            indicator_thread.start()

        image = self._isolate_face()
        self.close()

        if filename:
            filename = self.save_image_as_file(image, filename)
            return filename

        if indicator_thread:
            indicator_thread.stop()
        return image


    def save_image_as_file(self, image_array, filename):
        """
        If filename has no extension, then it is used as the extension.
        Eg filename == 'png' then, a default filename is generated, with a png extension.
        """
        # for row in image_array:
        #     print row
        im = Image.fromarray(image_array)
        #im.show()

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
        biggest_face_id = faces[0][0]

        framing = Framing(self.gray)

        # Get a tight image around the face
        face_rect = self.tracking.face_boundary(biggest_face_id)
        face_img = face_image.sub_image(
            self.frame, framing.tighten_rect(face_rect, self.threshold_zoom))

        # Get a framed image about the face
        final_img = face_image.sub_image(
            self.gray, framing.single_portrait(face_rect))

        # Blur and dynamically threshold it
        final_img = self.process_image(final_img)

        return final_img

    def _capture_frame(self):
        captured = False
        while not captured:
            captured, self.frame = self.camera.read()


        self.gray = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
        self.faces = self.face_cascade.detectMultiScale(self.gray, 1.3, 5)

        self.tracking.observe(self.faces)

        return self.frame

    def _wait_for_face_lock(self, indicator_thread=None):
        while True:
            print "hi"
            if not hasattr(self, 'faces') or self.faces == None or len(self.faces) == 0:
                self.last_highest = 0
            else:
                diff = self.tracking.score_max - self.last_highest
                print "Diff: %s" % diff
                diff = diff / 20.0
            self._capture_frame()
            # time.sleep(1)

            # Is a lock obtained?
            if self._face_lock_obtained():
                return

            if self.debug:
                self.tracking.highlight_faces(self.frame, 1)

                for face in self.faces:
                    (x, y, w, h) = face
                    cv2.rectangle(
                        self.frame, (x, y), (x + w, y + h),
                        (0, 0, 255), 1)

                cv2.imshow('frame', self.frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.close()
                raise Exception('User requested quit')

    def _face_lock_obtained(self):
        for face in self.tracking.evidence.values():
            self.last_highest = face['score'] if face['score'] > self.last_highest else self.last_highest
            if face['score'] == self.tracking.score_max:
                return True
        return False