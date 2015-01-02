import json
import os
from euclid import Vector2
from polarweb.config import settings
from polarweb.models.geometry import Rectangle

def relate_pages_to_machines():
    """
    Unpack the values from the settings file, create instances of Rectangle
    for the extents of both PAGES and MACHINES.

    :return:
    """

    for k in settings.PAGES:
        v = settings.PAGES[k]
        v['extent'] = Rectangle(Vector2(v['width'], v['height']), Vector2(v['x'], v['y']))
        v['name'] = k

    # unpack the machine details
    for k in settings.MACHINES:
        v = settings.MACHINES[k]
        v['extent'] = Rectangle(Vector2(v['width'], v['height']), Vector2(0, 0))
        v['name'] = k

    return settings

SETTINGS = relate_pages_to_machines()