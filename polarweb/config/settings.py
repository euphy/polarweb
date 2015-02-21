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

MACHINES = {
    "left": {
        "width": 725,
        "height": 980,
        "comm_port": "COM5",
        "baud_rate": 57600,
        "default_page": "A1"}
}

ARTWORK_ACQUIRE_METHOD = {
    "method_name": "acquire_face_track",
    "module": "polarweb.models.acquire"
}

CAMERA_NUM = 0