from polarweb.image_grabber.lib.app import ImageGrabber
from polarweb.pathfinder import workflow

grabber = ImageGrabber(debug=True)
img_filename = grabber.get_image(filename="png")
print "Got %s" % img_filename

image_paths = workflow.run(input_img=img_filename)