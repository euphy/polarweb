import threading
import cv2
import numpy as np
from polarweb import visualization
from polarweb.image_grabber.lib.app import ImageGrabber
from polarweb.pathfinder import workflow

grabber = ImageGrabber(debug=True)
img_filenames = grabber.get_images(filename="png")
print "Got %s" % img_filenames

tracing_thread = \
    threading.Thread(target=workflow.run,
                     kwargs={'input_img': img_filenames['final'] }).start()


def visualise_capture_process(img_filenames, tracing_thread):
    for key in img_filenames:
        print "%s: %s" % (key, img_filenames[key])

    sequence = [
        {'name': 'shutter',
         'duration': 0.5,
         'method': visualization.shutter},
        {'name': 'greyscaled',
         'duration': 2,
         'method': visualization.captioned_image,
         'kwargs': {'caption': 'Desaturated'},
         'filename_key': 'greyscale'},
        {'name': 'equalized',
         'duration': 2,
         'method': visualization.captioned_image,
         'kwargs': {'caption': 'Equalised'},
         'filename_key': 'equalized'},
        {'name': 'blurred',
         'duration': 2,
         'method': visualization.captioned_image,
         'kwargs': {'caption': 'Blurred'},
         'filename_key': 'blurred'},
        {'name': 'posterized',
         'duration': 2,
         'method': visualization.captioned_image,
         'kwargs': {'caption': 'Posterised'},
         'filename_key': 'posterized'},
        ]

    initial_frame = cv2.imread(img_filenames['raw'])
    for step in sequence:
        print step
        print "hello!"
        if 'kwargs' in step:
            step_input = cv2.imread(img_filenames[step['filename_key']])
            h, w = initial_frame.shape[:2]
            step_input = cv2.resize(step_input, (w, h))

            step_frame = step['method'](step_input, **step['kwargs'])
        else:
            step_frame = step['method'](initial_frame)

        cv2.imshow('visual', step_frame)
        cv2.waitKey(int(step['duration']*1000))
        print "waited %s" % int(step['duration']*1000)

    # Now display vector stuff
    vector_process_wait = \
        visualization.captioned_image(visualization.shutter(initial_frame),
                                      caption="Tracing image...")
    cv2.imshow('visual', vector_process_wait)
    cv2.waitKey(2000)






visualise_capture_process(img_filenames, tracing_thread)
# image_paths = workflow.run(input_img=img_filenames['final'])