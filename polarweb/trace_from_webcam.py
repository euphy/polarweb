import copy
import threading
import cv2
import numpy as np
from polarweb import visualization
from polarweb.image_grabber.lib.app import ImageGrabber
from polarweb.pathfinder import workflow
from polarweb.pathfinder.pathfinder_thread import PathfinderThread

grabber = ImageGrabber(debug=False)
img_filenames = grabber.get_images(filename="png")
print "Got %s" % img_filenames

tracing_thread = PathfinderThread(input_img=img_filenames['final'])
print tracing_thread.get_progress()
tracing_thread.start()

visualization.visualise_capture_process(img_filenames, tracing_thread)