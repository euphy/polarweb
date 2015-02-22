import os
import time

from PIL import Image
import numpy
from paths import build_graph, build_paths, filter_paths, paths2svg, paths2json
from polarweb.pathfinder.smoothing import apply_box_smoothing
from decimation import subsampling_decimation, anchor_angle_error, \
    total_divergence_error

def run(input_img='./sampleinput.png',
        min_path_len=20,
        max_path_count=100,
        smoothing_levels=3,
        scale=3):

    tic = time.clock()
    start_tic = tic

    # Load image data as bitmap matrix
    image = Image.open(input_img)
    imdata = numpy.asarray(image, dtype=numpy.uint8)

    graph = build_graph(imdata)
    toc = time.clock()
    print "Build graph in %s" % (toc - tic)
    paths = build_paths(graph)
    tic = time.clock()
    print "Build paths in %s" % (tic - toc)

    paths = filter_paths(paths,
                         min_length=min_path_len,
                         max_paths=max_path_count)
    toc = time.clock()
    print "Filtered in %s" % (toc - tic)

    paths = apply_box_smoothing(paths, passes=3)
    tic = time.clock()
    print "Smoothed in %s" % (tic - toc)

    # total_divergence_error is the smartest error function
    paths = subsampling_decimation(paths, total_divergence_error, 5)
    # anchor_angle_error with a low threshold is good for a final cleanup
    paths = subsampling_decimation(paths, anchor_angle_error, 0.05)
    toc = time.clock()
    print "Decimated in %s" % (toc - tic)

    # finally remove paths that have been decimated down to two three nodes
    paths = filter_paths(paths, min_length=3)
    tic = time.clock()
    print "Final filter in %s" % (tic - toc)

    name, ext = os.path.splitext(input_img)
    svg_filename = name + '.svg'
    json_filename = name + '.json'

    paths2svg(paths, image.size, svg_filename, scale=scale, show_nodes=False, outline=True)
    toc = time.clock()
    print "Saved SVG (%s) in %s" % (svg_filename, (toc - tic))

    paths2json(paths, json_filename)
    tic = time.clock()
    print "Saved JSON (%s) in %s" % (json_filename, (tic - toc))
    print "Path detection completed in %s" % (tic - start_tic)

    return paths

