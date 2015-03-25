from polarweb.image_grabber.lib.app import ImageGrabber

grabber = ImageGrabber(debug=True, input_image_filename="Robert-de-Niro1.jpg")
grabber.get_images(filename="png")