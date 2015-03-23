from collections import defaultdict
import sys

class Glyph():
    def __init__(self, paths):
        self.paths = paths
        self.first = paths[0]
        self.last = paths[1]

def build_glyphs(paths):
    gs = [Glyph(paths=path) for path in paths]
    initials = list()
    for g in gs:
        initials.append(g.first)
        initials.append(g.last)

    return gs, initials

def optimize_sequence(paths):
    # glyphs is a list of paths
    # initials is a list of start and end points
    glyphs, initials = build_glyphs(paths)
    print("Total Glyphs: %d" % len(glyphs))
    print("Total initials: %d" % len(initials))

    # sort the initials


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