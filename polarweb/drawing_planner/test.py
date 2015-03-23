import json
from polarweb.drawing_planner import optimize_sequence

__author__ = 'sandy_000'

with open('test.json', 'r') as data_file:
    paths = json.load(data_file)['paths']

opt_paths = optimize_sequence(paths)

