from random import randint
from euclid import Vector2
from polarweb.config import SETTINGS
from polarweb.models.geometry import Rectangle


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
                panel = Rectangle(size=Vector2(panel_size.x, panel_size.y), position=pos+origin)
                panels[(col, row)] = panel

        for key in panels.keys():
            panels[key].size.x = panels[key].size.x - 12
            panels[key].size.y = panels[key].size.y - 12
            panels[key].position.x += 6
            panels[key].position.y += 6

        return panels

    def use_random_panel(self):
        print "In random panel."
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
            print "Using key: %s, which is %s" % (key, self.get_current_panel())
            return self.get_current_panel()


    def use_next_panel(self):
        if hasattr(SETTINGS, 'USE_PANEL') and SETTINGS.USE_PANEL == 'random':
            return self.use_random_panel()

        # Else:
        print "In next panel."
        if not self.panels.keys():
            return None
        else:
            print "Raw order"
            for k in self.panels.keys():
                print k

            print "sorted"
            l = list(self.panels.keys())
            l.sort(cmp=Layout.coord_cmp)
            for k in l:
                print k
            self.current_panel_key = l[-1]
            print "Using key: %s, which is %s" % (self.current_panel_key,
                                                  self.get_current_panel())
            return self.get_current_panel()

    @classmethod
    def coord_cmp(cls, me, it):
        if me[1] == it[1]:
            c = cmp(me[0], it[0])
        else:
            c = cmp(me[1], it[1])
        return c

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
        self.current_panel_key = None

    def scale_to_panel(self, paths):
        p = self.get_current_panel()
        if not p:
            raise ValueError("No panel was available to scale to.")

        # determine a scaling factor

        # Turn them into floats
        for path_index, path in enumerate(paths):
            for point_index, point in enumerate(path):
                paths[path_index][point_index] = (float(point[0]), float(point[1]))

        paths_size = Layout.get_path_size(paths)
        print "Paths size: %s" % str(paths_size)

        panel_ratio = p.height_to_width()
        paths_ratio = paths_size[1] / float(paths_size[0])

        print "Panel ratio: %s" % panel_ratio
        print "Paths ratio: %s" % paths_ratio

        if panel_ratio > paths_ratio:
            scaling = p.size.x / paths_size[0]
        else:
            scaling = p.size.y / paths_size[1]

        print "Scaling: %s" % scaling
        for path_index, path in enumerate(paths):
            for point_index, point in enumerate(path):
                paths[path_index][point_index] = (point[0]*scaling, point[1]*scaling)

        print "transform: %s" % str(self.extent.position)
        for path_index, path in enumerate(paths):
            for point_index, point in enumerate(path):
                paths[path_index][point_index] = (point[0]+p.position.x,
                                                  point[1]+p.position.y)


        return paths

    @classmethod
    def get_path_size(cls, paths):
        x_max = 0
        y_max = 0
        for path in paths:
            for point in path:
                if point[0] > x_max: x_max = point[0]
                if point[1] > y_max: y_max = point[1]

        return (x_max, y_max)

    def panels_left(self):
        num = len(self.panels)
        if self.get_current_panel_key() and self.get_current_panel_key() in self.panels.keys():
            num -= 1

        return num