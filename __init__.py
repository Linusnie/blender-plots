import sys
import os

bl_info = {
    "name": "Blender Plots",
    "description": "Adds a python API for plotting in blender",
    "author": "Linus Härenstam-Nielsen",
    "version": (1, 0, 0),
    "blender": (3, 2, 0),
    "location": "Python console",
    "warning": "",
    "doc_url": "https://github.com/Linusnie/blender-plots",
    "tracker_url": "https://github.com/Linusnie/blender-plots/issues",
    "support": "COMMUNITY",
    "category": "Development",
}


def register():
    sys.path.append(os.path.dirname(__file__))


def unregister():
    sys.path.remove(os.path.dirname(__file__))
