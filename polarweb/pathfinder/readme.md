## pathfinder

A python module for generating paths from a posterized image to be efficiently
drawn by a polargraph machine.

Consists of a library of useful functions from which to construct workflows.

see *sample_workflow.py* for example.

Sample usage:

    >>> from pathfinder.sample_workflow import run
    >>> run(input_img='./pathfinder/sampleinput.png')

then examine the paths.svg and paths.json file in the present working directory.