from collections import defaultdict
import copy
import sys
from polarweb.pathfinder import paths2svg


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
    return gs


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
    n = [list((abs(i[0]-value[0]), abs(i[1]-value[1]))) for i in arr]
    idx = n.index(min(n))
    return arr[idx]


def distance_between(one, other):
    return abs(other[0] - one[0]) + abs(other[1] - one[1])

def total_travel(glyphs):
    if not glyphs:
        return 0

    travel = 0
    for g in glyphs:
        last = g.first
        for p in g.paths[1:]:
            d = distance_between(last, p)
            travel += d
            last = p
    return travel

def total_penup_travel(glyphs):
    if not glyphs:
        return 0

    travel = 0
    last = glyphs[0]
    for g in glyphs[1:]:
        d = distance_between(last.last, g.first)
        travel += d
        last = g
    return travel

def dedupe(gs):
    "Use Glyph.__hash__() to dedupe the list of glyphs"
    seen = set()
    for g in gs:
        h = hash(g)
        if h not in seen:
            yield g
            seen.add(h)


def reorder_greedy(glyphs):
    gs = copy.copy(glyphs)
    initials = list()
    for g in gs:
        initials.append(g.first)
        initials.append(g.last)

    print("Total Glyphs: %d" % len(gs))
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
        # . Find an initial closest to the last glyph's terminal point
        next = find_nearest(initials, last)

        glyph = extract_glyph_with_initial(gs, next)
        glyph = make_initial_first(glyph, next)
        queue.append(glyph)

        #. Remove the glyph's end points from initials
        initials.remove(glyph.first)
        initials.remove(glyph.last)

        last = glyph.last

    return queue

def save_svg(paths, suffix):
    svg_filename = "_".join(("test", suffix)) + ".svg"
    paths2svg(paths, (500,500), svg_filename,
              scale=1,
              show_nodes=True,
              outline=True)
    return svg_filename


def optimize_sequence(paths):
    # glyphs is a list of paths
    # initials is a list of start and end points
    glyphs = build_glyphs(paths)
    print("Initial penup distance: %9d" % total_penup_travel(glyphs))
    print("Initial total distance: %9d" % total_travel(glyphs))
    # save_svg([ps.paths for ps in glyphs], "basic")

    # dedupe alone (and used below)
    glyphs_deduped = list(dedupe(glyphs))
    print("Deduped penup distance: %9d" % total_penup_travel(glyphs_deduped))
    print("Deduped total distance: %9d" % total_travel(glyphs_deduped))
    
    # easy sort: sort all glyphs by starting point
    #
    # This is O(n log n) because it's simply a sort.
    glyphs_sorted = sorted(glyphs, key=lambda st: st.first)
    print("Sorted penup distance:  %9d" % total_penup_travel(glyphs_sorted))
    print("Sorted total distance:  %9d" % total_travel(glyphs_sorted))
    # save_svg([ps.paths for ps in glyphs_sorted], "sorted")

    glyphs_reordered = reorder_greedy(glyphs)
    print("Greedy penup:  %9d" % (total_penup_travel(glyphs_reordered)))
    print("Greedy total:  %9d" % (total_travel(glyphs_reordered)))
    save_svg([ps.paths for ps in glyphs_reordered], "reordered")

    # paths_out = [ps.paths for ps in glyphs_reordered]
    # paths_out = [ps.paths for ps in glyphs_sorted]
    paths_out = [ps.paths for ps in glyphs_reordered]
    return paths_out
