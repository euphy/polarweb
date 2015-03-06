import os
from threading import Thread
import time

from PIL import Image
import numpy
from paths import build_graph, build_paths, filter_paths, paths2svg, paths2json
from polarweb.pathfinder.smoothing import apply_box_smoothing
from decimation import subsampling_decimation, anchor_angle_error, \
    total_divergence_error

class PathfinderThread(Thread):

    progress = [{'name': 'Tracing', 'status': "Not started"},
                {'name': 'Building graph', 'status': "Not started"},
                {'name': 'Building paths', 'status': "Not started"},
                {'name': 'Filtering paths', 'status': "Not started"},
                {'name': 'Smoothing paths', 'status': "Not started"},
                {'name': 'Decimating paths', 'status': "Not started"},
                {'name': 'Cleanup paths', 'status': "Not started"},
                {'name': 'Saving SVG', 'status': "Not started"},
                {'name': 'Saving JSON', 'status': "Not started"},
                {'name': 'Finished', 'status': "Not started"}]
    progress_stage = -1

    process_start = 0.0
    stage_start = 0.0
    stage_tic = 0.0


    def __init__(self,
            input_img='./sampleinput.png',
            min_path_len=20,
            max_path_count=100,
            smoothing_levels=3,
            scale=3,
            event_callback=None):
        Thread.__init__(self)
        self.input_img = input_img
        self.min_path_len = min_path_len
        self.max_path_count = max_path_count
        self.smoothing_levels = smoothing_levels
        self.scale = scale
        self.filename, ext = os.path.splitext(self.input_img)
        self.event_callback = event_callback

        print "STart tracing thread."

    def run(self):
        self.progress_stage = 0

        # Set up timing stuff
        slug_factor = 2
        self.process_start = time.clock()
        self.stage_start = self.process_start
        self.stage_tic = self.process_start
        
        self.progress[self.progress_stage]['status'] = 'Started'
        self.progress_stage = 1
        self.progress[self.progress_stage]['status'] = 'Started'
        # Load image data as bitmap matrix
        image = Image.open(self.input_img)
        imdata = numpy.asarray(image, dtype=numpy.uint8)

        graph = build_graph(imdata)
        self.stage_tic = time.clock()

        print "Build graph in %s" % (self.stage_tic - self.stage_start)
        self.progress[self.progress_stage]['status'] = "%ss" % \
                                        (self.stage_tic - self.stage_start)
        self.stage_start = time.clock()
        self.progress_stage = 2
        self.progress[self.progress_stage]['status'] = 'Started'
        paths = build_paths(graph)
        svg_filename = self.save_svg(paths, image.size, "00_paths")
        self.progress[self.progress_stage]['filename'] = svg_filename

        time.sleep(slug_factor*2)
        self.stage_tic = time.clock()
        print "Build paths in %s" % (self.stage_tic - self.stage_start)
        self.progress[self.progress_stage]['status'] = "%ss" % \
                                        (self.stage_tic - self.stage_start)
        self.stage_start = time.clock()
        self.progress_stage = 3
        self.progress[self.progress_stage]['status'] = 'Started'

        paths = filter_paths(paths,
                             min_length=self.min_path_len,
                             max_paths=self.max_path_count)
        svg_filename = self.save_svg(paths, image.size, "01_filtered")
        self.progress[self.progress_stage]['filename'] = svg_filename
        time.sleep(slug_factor)

        self.stage_tic = time.clock()
        print "Filtered in %s" % (self.stage_tic - self.stage_start)
        self.progress[self.progress_stage]['status'] = "%ss" % \
                                        (self.stage_tic - self.stage_start)
        self.stage_start = time.clock()
        self.progress_stage = 4
        self.progress[self.progress_stage]['status'] = 'Started'

        paths = apply_box_smoothing(paths, passes=3)
        svg_filename = self.save_svg(paths, image.size, "02_smoothed")
        self.progress[self.progress_stage]['filename'] = svg_filename
        time.sleep(slug_factor)
        self.stage_tic = time.clock()
        print "Smoothed in %s" % (self.stage_tic - self.stage_start)
        self.progress[self.progress_stage]['status'] = "%ss" % \
                                        (self.stage_tic - self.stage_start)
        self.stage_start = time.clock()
        self.progress_stage = 5
        self.progress[self.progress_stage]['status'] = 'Started'

        # total_divergence_error is the smartest error function
        paths = subsampling_decimation(paths, total_divergence_error, 5)
        # anchor_angle_error with a low threshold is good for a final cleanup
        paths = subsampling_decimation(paths, anchor_angle_error, 0.05)
        svg_filename = self.save_svg(paths, image.size, "03_decimated")
        self.progress[self.progress_stage]['filename'] = svg_filename
        time.sleep(slug_factor)
        self.stage_tic = time.clock()
        print "Decimated in %s" % (self.stage_tic - self.stage_start)
        self.progress[self.progress_stage]['status'] = "%ss" % \
                                        (self.stage_tic - self.stage_start)
        self.stage_start = time.clock()
        self.progress_stage = 6
        self.progress[self.progress_stage]['status'] = 'Started'

        # finally remove paths that have been decimated down to two three nodes
        paths = filter_paths(paths, min_length=3)
        self.progress[self.progress_stage]['filename'] = svg_filename
        time.sleep(slug_factor)
        self.stage_tic = time.clock()
        print "Final filter in %s" % (self.stage_tic - self.stage_start)
        self.progress[self.progress_stage]['status'] = "%ss" % \
                                        (self.stage_tic - self.stage_start)
        self.stage_start = time.clock()
        self.progress_stage = 7
        self.progress[self.progress_stage]['status'] = 'Started'
        svg_filename = self.save_svg(paths, image.size, "05_final")
        self.progress[self.progress_stage]['filename'] = svg_filename
        time.sleep(slug_factor)
        self.stage_tic = time.clock()
        print "Saved SVG (%s) in %ss" % (svg_filename, (self.stage_tic - self.stage_start))
        self.progress[self.progress_stage]['status'] = "%ss" % \
                                        (self.stage_tic - self.stage_start)
        self.stage_start = time.clock()
        self.progress_stage = 8
        self.progress[self.progress_stage]['status'] = 'Started'

        json_filename = self.filename + '.json'
        paths2json(paths, json_filename)
        time.sleep(slug_factor)
        self.stage_tic = time.clock()
        print "Saved JSON (%s) in %s" % (json_filename, (self.stage_tic - self.stage_start))
        print "Path detection completed in %ss" % \
                                        (self.stage_tic - self.process_start)
        self.progress[self.progress_stage]['status'] = "%ss" % \
                                        (self.stage_tic - self.stage_start)
        self.progress_stage = 9
        self.progress[self.progress_stage]['status'] = 'Started'
        self.progress[self.progress_stage]['paths'] = paths

        return paths

    def get_progress(self):
        if self.progress_stage != -1:
            self.progress[self.progress_stage]['status'] = "%.2f seconds" % \
                                    (time.clock() - self.stage_start)

        return self.progress, self.progress[self.progress_stage]

    def get_result_stage(self, stage):
        if stage <= self.progress_stage:
            return self.progress[stage]['filename']

    def save_svg(self, paths, size, suffix):
        svg_filename = "_".join((self.filename, suffix)) + ".svg"
        paths2svg(paths, size, svg_filename,
                  scale=self.scale,
                  show_nodes=False, outline=True)
        return svg_filename


