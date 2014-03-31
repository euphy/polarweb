from datetime import datetime
from lib.app import ImageGrabber

grabber = ImageGrabber(debug=True)
grabber.get_image(filename="png")