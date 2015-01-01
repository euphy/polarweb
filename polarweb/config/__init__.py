import json
import os
from euclid import Vector2
from polarweb.config import settings
from polarweb.models.geometry import Rectangle

def relate_pages_to_machines():
    for k in settings.pages:
        v = settings.pages[k]
        v['extent'] = Rectangle(Vector2(v['width'], v['height']), Vector2(v['x'], v['y']))
        v['name'] = k

    # unpack the machine details
    for k in settings.machines:
        v = settings.machines[k]
        v['extent'] = Rectangle(Vector2(v['width'], v['height']), Vector2(0, 0))
        v['name'] = k

        return settings

SETTINGS = relate_pages_to_machines()