from polarweb.image_grabber.lib.app import ImageGrabber

grabber = ImageGrabber(debug=True, blur=6)
grabber.get_image(filename="png")