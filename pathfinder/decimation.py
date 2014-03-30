"""
Functions and helper functions for decimating (lossily compressing) paths.
"""

# LET THERE BE FLOATING POINT DIVISION!
from __future__ import division
#  and there was floating point division.

import numpy


def subsampling_decimation(paths, error_function, error_threshold):
    """
    Subsampling decimation simplifies paths by removing as many nodes as
    possible, strategically in order to maintain a semblance of the paths'
    geometry.

    The outcome of the algorithm depends upon the specified error function and
    error threshold.

    The strategy for deciding which nodes to remove consists of designating an
    anchor node (initially the first node in the path), and then evaluating
    each subsequent node in sequence as a candidate for removal until an
    ineligible node (i.e. a node with an error relative to the base node which
    is greater than the threshold) is found, at which point all nodes in
    between but excluding the anchor node and the last eligible node are
    removed.

    The last eligible node (which now follows directly after the anchor node),
    is then designated as the new anchor node, and the process is repeated.
    """
    for path_index, path in enumerate(paths):
        new_path = path[:1]
        anchor_index = 0

        while anchor_index in range(len(path)):
            anchor_node = path[anchor_index]

            collapse_count = 1

            for i, next_node in enumerate(path[anchor_index+2:]):

                if anchor_node == next_node:
                    # closed loop ... is this a bad?
                    #raise "a closed loop? ... that was unexpected."
                    # just move on without collapsing anything after this node
                    collapse_count = 1
                    break

                # feed the error function the path segment from the anchor node
                #  to the node being evaluated
                error = error_function(path[anchor_index:anchor_index+i+2])
                if error > error_threshold:
                    # fallback to last node eligible for removal, or the anchor
                    #  node
                    collapse_count -= 1
                    break
                else:
                    collapse_count += 1

            if anchor_index == len(path) - 1:
                new_path.append(path[anchor_index])
            else:
                new_path.append(path[anchor_index+collapse_count])
            anchor_index += collapse_count

        paths[path_index] = new_path

    return paths


##                                                                           ##
##  Helper functions, for use in error Functions                             ##
##                                                                           ##


def angle(v1, v2):
    """
    Returns the angle in radians between vectors 'v1' and 'v2'
    """
    v1_u = v1 / numpy.linalg.norm(v1)
    v2_u = v2 / numpy.linalg.norm(v2)
    angle = numpy.arccos(numpy.dot(v1_u, v2_u))
    if numpy.isnan(angle):
        if (v1_u == v2_u).all():
            return 0.0
        else:
            return numpy.pi
    return angle


def vector_magnitude(v):
    """
    Returns the scalar magnitude (length) of the vector `v`.
    """
    return numpy.sqrt(numpy.dot(v, v))


def distance_from_node_to_line_segment(node, linesegment):
    """
    Returns the distance from the point of `node` to the nearest point on
    `linesegment`.

    Algorithm works by examining the properties of the triangle ABC where AB is
    the line segment and C is the point, and D is the point on the line of AB
    at which (AB) is intersected by the line perpendicular to AB which subsumes
    the point C.
    """

    a = linesegment[0]
    b = linesegment[1]
    c = node

    ab_distance = vector_magnitude((a[0]-b[0], a[1]-b[1]))
    ca_distance = vector_magnitude((c[0]-a[0], c[1]-a[1]))
    cb_distance = vector_magnitude((c[0]-b[0], c[1]-b[1]))

    # This bit of mathgic produces the shorted distance from the point of
    # `node` to the line of `linesegment`
    lineseg_vector = (a[0]-b[0], a[1]-b[1])
    cross_prod = numpy.cross(lineseg_vector, (a[0]-c[0], a[1]-c[1]))
    cd_distance = numpy.abs(
        vector_magnitude(cross_prod) / vector_magnitude(lineseg_vector)
    )

    if ca_distance < ab_distance and cb_distance < ab_distance:
        # AB is the long side of ABC so D must between A and B
        return cd_distance

    # Determine whether D lies between A and B by considering the right angle
    # triangle ACD (if CA is longer than CB) or BCD (if CB is longer than CA).
    # If AD (or BD) is shorted than AB then D is on the line segment AB,
    # othewise it is elsewhere on the line of AB.

    if ca_distance > cb_distance:
        # angle between ab and ac
        angle_A = angle((b[0]-a[0], b[1]-a[1]), (c[0]-a[0], c[1]-a[1]))
        ad_distance = numpy.cos(angle_A) * ca_distance
        if ad_distance < ab_distance:
            return cd_distance
        else:
            return cb_distance

    else:
        # angle between ba and bc
        angle_B = angle((a[0]-b[0], a[1]-b[1]), (c[0]-b[0], c[1]-b[1]))
        bd_distance = numpy.cos(angle_B) * cb_distance
        if bd_distance < ab_distance:
            return cd_distance
        else:
            return ca_distance


##                                                                           ##
##  Error functions, for use by the subsampling_decimation funtion           ##
##                                                                           ##


def anchor_angle_error(path_segment):
    """
    Returns the angle in radians between the vector of the initial edge in this
    path, and the vector from the anchor node to final node in the sequence.
    """
    anchor_vector = (path_segment[1][0]-path_segment[0][0],
                     path_segment[1][1]-path_segment[0][1])
    full_vector = (path_segment[-1][0]-path_segment[0][0],
                   path_segment[-1][1]-path_segment[0][1])
    return angle(anchor_vector, full_vector)


def right_angled_area_error(path_segment):
    """
    Returns the area of the right angle triangle which has the line from the
    initial node to the final as its hypotenuse, and one side that includes the
    initial edge of the path as a subsegment.

    Prone to undesirable behavoir, especially with higher thresholds, if the
    initial edge happens to be at un unrepresentative angle.
    """
    if len(path_segment) < 3:
        return 0

    anchor_vector = (path_segment[1][0]-path_segment[0][0],
                     path_segment[1][1]-path_segment[0][1])
    full_vector = (path_segment[-1][0]-path_segment[0][0],
                   path_segment[-1][1]-path_segment[0][1])
    theta = angle(anchor_vector, full_vector)

    # calculate the area of the right angled triangle including linesegment
    #  `full_vector` and angle `theta`
    hypotenuse = vector_magnitude(full_vector)
    adjacent = numpy.cos(theta) * hypotenuse
    opposite = numpy.sin(theta) * hypotenuse
    area = adjacent * opposite / 2
    return area


def max_divergence_error(path_segment):
    """
    Returns the maximum distance of a node in the path from the line segment
    defined by the initial and final nodes.
    """
    if len(path_segment) < 3:
        return 0

    full_lineseg = (path_segment[0], path_segment[-1])

    return max([distance_from_node_to_line_segment(node, full_lineseg)
                for node in path_segment[1:-1]])


def total_divergence_error(path_segment):
    """
    Returns the maximum distance of a node in the path from the line segment
    defined by the initial and final nodes.

    This function produces a decent approximation of the change of shape
    incurred by replacing the given path segment with a single edge.
    """
    if len(path_segment) < 3:
        return 0

    full_lineseg = (path_segment[0], path_segment[-1])

    return sum([distance_from_node_to_line_segment(node, full_lineseg)
                for node in path_segment[1:-1]])
