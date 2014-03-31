POLARWEB
========

Work in progress.
This is software produced as part of the emerging *Polargraph Pro* project.

Architecture
------------

The central artefact here is a couple of Polargraph machine "model" objects, 
and a web UI for controlling it. This is all pretty simple stuff, but is the 
core of the new Polargraph control software. 

Secondarily, there are fairly sophisticated helper routines that are interested 
in capturing faces from a webcam (image_grabber), and converting them into vector 
artwork (pathfinder, contributed by nat-n) that are drawable using the polargraph machine. 

These are in this repo, but are entirely separate to the central _polarweb_ project 
in the sense that they have their own requirements and libraries, and getting one 
working doesn't necessarily mean the rest are working.

Automatic
---------

The first project goal is to make the machine automatic. It will hunt for faces when idle, 
and then draw what it finds into a set of available panels on a page. When all the panels
are full, then it will beg for attention (new sheet, please).

Requirements
------------

Mercifully, it's all turned out to be in Python. It is targetting a Windows environment, so 
I think there is some stupid in there somewhere.

Core:
* pyserial
* numpy
* euclid
* requests
* flask
* flask-assets
* jsmin
http://pyserial.sourceforge.net/

Image Grabber:
* OpenCV 2.* (cv2)

http://opencvpython.blogspot.in/2012/05/install-opencv-in-windows-for-python.html
http://stackoverflow.com/questions/10417108/what-is-different-between-all-these-opencv-python-interfaces

Pathfinder:
* Pillow

http://stackoverflow.com/questions/7133193/what-is-going-on-with-pil-and-the-import-statement

Resources
---------

[Scriptdraw SVG test renderer] (http://scriptdraw.com/)
