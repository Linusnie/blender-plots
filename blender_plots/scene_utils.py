import math

import bpy
import numpy as np

import blender_plots as bplt
from blender_plots import blender_utils as bu


def create_camera(location, rotation):
    if "Camera" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Camera"])

    bpy.ops.object.camera_add(
        enter_editmode=False, align="VIEW", location=location, rotation=rotation
    )
    bpy.context.scene.camera = bpy.data.objects["Camera"]


def render_image(output_path, resolution=None, samples=100):
    if resolution is not None:
        bpy.context.scene.render.resolution_x = resolution[0]
        bpy.context.scene.render.resolution_y = resolution[1]
    bpy.context.scene.cycles.samples = samples
    bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)


def setup_scene(
    clear=False,
    camera_location=None,
    camera_rotation=None,
    resolution=None,
    sun_energy=10,
):
    """Example function for setting up a scene for rendering."""
    if camera_location is None:
        camera_location = np.array([0, -5.321560, 2.042498]) * 0.6
    if camera_rotation is None:
        camera_rotation = [math.radians(68.4), 0.0, 0.0]

    if clear:
        bpy.ops.wm.read_homefile()
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (
        1,
        1,
        1,
        1,
    )
    bpy.context.scene.render.engine = "CYCLES"
    bpy.data.scenes["Scene"].cycles.samples = 256

    if "Light" in bpy.data.objects:
        # remove default light
        bpy.data.objects.remove(bpy.data.objects["Light"])
    if "Sun" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Sun"])
    bpy.ops.object.light_add(
        type="SUN", radius=1, align="WORLD", location=(0, 0, 0), scale=(1, 1, 1)
    )
    bpy.data.objects["Sun"].data.energy = sun_energy
    bpy.data.objects["Sun"].data.angle = np.pi / 2
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[
        "Strength"
    ].default_value = 0.5

    bpy.context.scene.render.film_transparent = True
    create_camera(camera_location, camera_rotation)
    if resolution is not None:
        bpy.context.scene.render.resolution_x = resolution[0]
        bpy.context.scene.render.resolution_y = resolution[1]
