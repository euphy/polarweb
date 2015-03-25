import json
from polarweb.drawing_planner import optimize_sequence

__author__ = 'sandy_000'

with open('20150325-223051.5640009816.json', 'r') as data_file:
    paths = json.load(data_file)['paths']

optimised_paths = optimize_sequence(paths)


