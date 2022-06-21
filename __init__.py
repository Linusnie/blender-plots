bl_info = {
    "name": "Blender Plots",
    "description": "Adds python API for plotting in blender",
    "author": "Linus Härenstam-Nielsen",
    "version": (1, 0, 0),
    "blender": (3, 1, 2),
    "location": "Python console",
    "warning": "",
    "doc_url": "",
    "tracker_url": "",
    "support": "COMMUNITY",
    "category": "Development",
}

from .scatter import *
from .blender_utils import *


def register():
    pass


def unregister():
    pass
