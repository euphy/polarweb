import json
import os
from euclid import Vector2
from polarweb.models.geometry import Rectangle


def load_config_from_json():

    config_file_name = 'config.json'
    config_path = os.path.join(os.path.dirname(__file__), config_file_name)

    with open(config_path, 'r') as data_file:
        data = json.load(data_file)

        # unpack the pages details
        for k in data['pages']:
            v = data['pages'][k]
            v['extent'] = Rectangle(Vector2(v['width'], v['height']), Vector2(v['x'], v['y']))
            v['name'] = k

        # unpack the machine details
        for k in data['machines']:
            v = data['machines'][k]
            v['extent'] = Rectangle(Vector2(v['width'], v['height']), Vector2(0,0))
            v['name'] = k


        return data

SETTINGS = load_config_from_json()