# TODO fix library path once instead of repeating this in every file
# currently, random import statements are altering the path so
# transitive dependencies are prone to breaking in exciting ways.
import os
import sys

sys.path.append(os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, "libs")))
