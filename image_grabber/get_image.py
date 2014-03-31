from datetime import datetime
from lib.app import ImageGrabber

grabber = ImageGrabber(debug=True)
image = grabber.get_image(filename="png")
print image