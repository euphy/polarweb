import os
from PIL import Image

import numpy

from paths import build_graph, build_paths, filter_paths, paths2svg, paths2json
from smoothing import apply_box_smoothing
from decimation import subsampling_decimation, anchor_angle_error, \
    right_angled_area_error, max_divergence_error, total_divergence_error


def run(input_img='./sampleinput.png',
        min_path_len=20,
        max_path_count=100,
        smoothing_levels=3,
        scale=3):

    # Load image data as bitmap matrix
    image = Image.open(input_img)
    imdata = numpy.asarray(image, dtype=numpy.uint8)

    graph = build_graph(imdata)
    paths = build_paths(graph)

    paths = filter_paths(paths,
                         min_length=min_path_len,
                         max_paths=max_path_count)

    paths = apply_box_smoothing(paths, passes=3)

    # total_divergence_error is the smartest error function
    paths = subsampling_decimation(paths, total_divergence_error, 5)
    # anchor_angle_error with a low threshold is good for a final cleanup
    paths = subsampling_decimation(paths, anchor_angle_error, 0.05)

    # finally remove paths that have been decimated down to two three nodes
    paths = filter_paths(paths, min_length=3)


    name, ext = os.path.splitext(input_img)
    svg_filename = name + '.svg'
    json_filename = name + '.json'

    paths2svg(paths, image.size, svg_filename, scale=scale, show_nodes=False)
    paths2json(paths, json_filename)

    return paths
