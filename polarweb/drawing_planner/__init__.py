from collections import defaultdict
import sys

class Glyph():
    def __init__(self, paths):
        self.paths = paths
        self.first = paths[0]
        self.last = paths[-1]

    def reverse(self):
        self.paths.reverse()
        self.first = self.paths[0]
        self.last = self.paths[-1]

def build_glyphs(paths):
    gs = [Glyph(paths=path) for path in paths]
    initials = list()
    for g in gs:
        initials.append(g.first)
        initials.append(g.last)

    return gs, initials


def extract_glyph_with_initial(glyphs, initial):
    for g in glyphs[:]:
        if initial in (g.first, g.last):
            glyphs.remove(g)
            return g

    raise Exception("There was no glyph with the initial %s" % initial)


def make_initial_first(g, initial):
    if g.first == initial:
        return g
    elif g.last == initial:
        g.reverse()
        return g
    else:
        raise Exception("Initial (%s) was not in glyph" % initial)

def find_nearest(arr, value):
    print "Arr: %s" % arr
    print "Value: %s" % value
    n = [list((abs(i[0]-value[0]), abs(i[1]-value[1]))) for i in arr]
    idx = n.index(min(n))
    return arr[idx]

def optimize_sequence(paths):
    # glyphs is a list of paths
    # initials is a list of start and end points
    glyphs, initials = build_glyphs(paths)
    print("Total Glyphs: %d" % len(glyphs))
    print("Total initials: %d" % len(initials))

    """
    #. Pick an initial.

    start
    #. Find a glyph with this as a first or last
    #. Remove the glyph from the list of available glyphs
    #. If it is a last, then reverse the glyph's points
    #. Add the glyph to the queue
    #. Remove the glyph's terminal point from initials
    #. Find an initial closest to the last glyph's terminal point
    go back to start until there are no glyphs left

    """

    queue = list()

    initials.sort()
    last = initials[0]

    while initials:
        #. Find an initial closest to the last glyph's terminal point
        next = find_nearest(initials, last)

        glyph = extract_glyph_with_initial(glyphs, next)
        glyph = make_initial_first(glyph, next)
        queue.append(glyph)

        #. Remove the glyph's end points from initials
        initials.remove(glyph.first)
        initials.remove(glyph.last)

        last = glyph.last

    # No sorting
    print("Initial penup distance: %9d" % total_penup_travel(glyphs))
    print("Initial total distance: %9d" % total_travel(glyphs))
    
    # dedupe alone (and used below)
    glyphs = list(dedupe(glyphs))
    print("Deduped penup distance: %9d" % total_penup_travel(glyphs))
    print("Deduped total distance: %9d" % total_travel(glyphs))
    
    # easy sort: sort all glyphs by starting point
    #
    # This is O(n log n) because it's simply a sort.
    sorted_g = sorted(glyphs,
                      key=lambda st: st.start or tuple())  # add default key in case 'start' is missing.
    print("Sorted penup distance:  %9d" % total_penup_travel(sorted_g))
    print("Sorted total distance:  %9d" % total_travel(sorted_g))

    greedy = reorder_greedy(glyphs)
    print("Greedy penup:  %9d" % (total_penup_travel(greedy)))
    print("Greedy total:  %9d" % (total_travel(greedy)))

    return greedy