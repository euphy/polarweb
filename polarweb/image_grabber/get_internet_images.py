import base64
from cStringIO import StringIO
import io
from polarweb.image_grabber.lib.app import ImageGrabber
import requests

# make a query, get a list of candidate images
url = "https://ajax.googleapis.com/ajax/services/search/images?v=1.0&q=manyfaces"
r = requests.get(url)
if r.status_code != 200:
    print "Oh no! Error %s" % r.status_code
    exit()

j = r.json()
for result in j['responseData']['results']:
    image_url = result['unescapedUrl']
    print image_url
    file_name_string = base64.urlsafe_b64encode(image_url)
    image_data = requests.get(image_url, stream=True)
    with io.open(file_name_string, 'wb') as f:
        f.write(StringIO(image_data.content).read())
    print

    grabber = ImageGrabber(debug=False, input_image_filename=file_name_string)
    grabber.get_image(filename="png")