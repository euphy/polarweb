from random import randint

__author__ = 'sandy_000'

from euclid import Point2, Vector2

class Rectangle():
    size = Vector2()
    position = Vector2()

    def __init__(self, size=Vector2(100, 100),
                 position=Vector2(0, 0)):
        self.size = size
        self.position = position

    def contains(self, p):
        return self.position.x < p.x < (self.size.x + self.position.x) \
                and self.position.y < p.y < (self.size.y + self.position.y)

    def __str__(self):
        return u"Rectangle size %s,%s and pos %s,%s" % (self.size.x, self.size.y, self.position.x, self.position.y)

class Layout():
    def __init__(self, extent, design):
        self.extent = extent
        self.design = design
        self.panels = Layout.init_panels(extent, design)
        self.current_panel_key = None

    @classmethod
    def init_panels(self, extent, design):
        """
        Extent is a Rectangle: size and position, specifying the area that should be subdivided.
        This would commonly correspond to the sheet of paper hung up to draw on.
        """
        splitted = design.split("x")
        horizontal_divider = int(splitted[0])
        vertical_divider = int(splitted[1])

        panel_width = extent.size.x / float(horizontal_divider)
        panel_height = extent.size.y / float(vertical_divider)
        panel_size = Vector2(panel_width, panel_height)
        origin = extent.position

        panels = {}
        count = 0

        for row in range(0, vertical_divider):
            for col in range(0, horizontal_divider):
                pos = Vector2(col*panel_width, row*panel_height)
                panel = Rectangle(size=panel_size, position=pos+origin)
                panels[(col, row)] = panel

        return panels

    def use_random_panel(self):
        if not self.panels.keys():
            return None
        else:
            number_of_keys = len(self.panels.keys())
            k_index = randint(0, number_of_keys-1)
            print "Num of keys: %s" % number_of_keys
            print "K index: %s" % k_index
            print "Keys: %s" % self.panels.keys()
            key = self.panels.keys()[k_index]
            self.current_panel_key = key
            return self.get_current_panel()

    def get_current_panel(self):
        if self.current_panel_key:
            return self.panels[self.current_panel_key]
        else:
            return None

    def get_current_panel_key(self):
        return self.current_panel_key

    def remove_current_panel(self):
        self.remove_panel(self.current_panel_key)
        self.current_panel_key = None
        return

    def remove_panel(self, key):
        panel = self.panels.pop(key, None)
        return panel

    def clear_panels(self):
        self.panels.clear()

    def scale_to_panel(self, paths):
        p = self.get_current_panel()
        if not p:
            raise ValueError("No panel was available to scale to.")

        # determine a scaling factor
        return paths

