PAGES = {
    "A1": {
        "width": 450,
        "height": 550,
        "x": 125,
        "y": 150},
    "A4": {
        "width": 450,
        "height": 550,
        "x": 125,
        "y": 150}
}

DEFAULT_PAGE = "A1"

MACHINES = [
    {"name": "left",
     "spec": {
        "width": 725,
        "height": 980,
        "comm_port": "COM8",
        "baud_rate": 57600,
        "default_page": "A1"}
    }
    ,
    {"name": "right",
     "spec": {
        "width": 725,
        "height": 980,
        "comm_port": "COM9",
        "baud_rate": 57600,
        "default_page": "A1"}
    }
]

ARTWORK_ACQUIRE_METHOD = {
    "method_name": "acquire_face_track",
    "module": "polarweb.models.acquire"
}

CAMERA_NUM = 0

# Values are 'none' or 'rotate cw'
CAMERA_ORIENTATION = 'rotate cw'