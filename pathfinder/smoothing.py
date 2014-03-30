# LET THERE BE FLOATING POINT DIVISION!
from __future__ import division
#  and there was floating point division.


def apply_box_smoothing(paths, passes=1):
    """
    Smoothing removes hard edges from path geometry without affecting topology.

    Equivalent to applying a 1D convolution with the following kernal [1,1,1],
    which has the effect of moving every node to the unweighted average
    position of itself and its imediate neighbors.

    `passes` is the number of times to apply the smoothing.
    """
    for path_index, path in enumerate(paths):
        for _ in xrange(passes):
            paths[path_index] = path = [
                (
                    (
                        (path[i-1][0] + node[0] + path[i+1][0]) / 3,
                        (path[i-1][1] + node[1] + path[i+1][1]) / 3
                    ) if i and len(path)-i-1 else node
                ) for i, node in enumerate(path)
            ]

    return paths
