import numbers
from dataclasses import dataclass

import bpy
import mathutils as mu
import numpy as np

import blender_plots.blender_utils as bu
from blender_plots import plots_base


@dataclass
class Constants:
    MARKER_SCALE = "marker_Scale"
    MARKER_ROTATION = "marker_rotation"
    MARKER_TYPES = {
        "cones": "GeometryNodeMeshCone",
        "cubes": "GeometryNodeMeshCube",
        "cylinders": "GeometryNodeMeshCylinder",
        "grids": "GeometryNodeMeshGrid",
        "ico_spheres": "GeometryNodeMeshIcoSphere",
        "circles": "GeometryNodeMeshCircle",
        "lines": "GeometryNodeMeshLine",
        "uv_spheres": "GeometryNodeMeshUVSphere",
    }


class Scatter(plots_base.Plot):
    """Create a scatterplot.

    Args:
        x,y,z:
            If y and z are not provided: expects x to be a Nx3 array with xyz positions for points to scatter, or TxNx3
                for sequence of scatter plots to animate
            if y and z are provided: expects x,y,z to be length N or TxN arrays for xyz coordinates respectively.
        color: (Tx)Nx3 or (Tx)Nx4 array or with RGB or RGBA values for each point and (optionally) time,
            or a single RGB/RGBA-value (e.g. (1, 0, 0) for red) to apply to every point.
        name: name to use for blender object. Will delete any previous plot with the same name.
        marker_type: select appearance of points. Either MARKER_TYPE, "spheres", bpy_types.Mesh or bpy_types.Object
        marker_rotation: (Tx)Nx3 (euler angles in radians) or (Tx)Nx3x3 (rotation matrices) array specifying the rotation for
            each point and (optionally) time.
        randomize_rotation: If set to True randomize the rotation of each marker. Overrides marker_rotation.
        marker_kwargs: additional arguments for configuring markers
    """

    def __init__(
        self,
        x,
        y=None,
        z=None,
        color=None,
        name="scatter",
        marker_type="ico_spheres",
        marker_scale=None,
        marker_rotation=None,
        randomize_rotation=False,
        **marker_kwargs,
    ):
        super().__init__(x, y, z, color=color, name=name, n_dims=1)

        if marker_type == "spheres":
            node_linker = add_sphere_markers(
                self.modifier, n_frames=self.n_frames, **marker_kwargs
            )
        elif marker_type is not None:
            node_linker = add_mesh_markers(
                self.modifier,
                randomize_rotation=randomize_rotation,
                marker_type=marker_type,
                set_scale=marker_scale is not None,
                n_frames=self.n_frames,
                with_color=color is not None,
                **marker_kwargs,
            )
        else:
            node_linker = bu.get_node_linker(self.modifier)
            node_linker.new_input_socket("Point Color", "NodeSocketMaterial")

        self.modifier[node_linker.input_sockets["Point Color"]] = self.color_material
        self.marker_rotation = marker_rotation
        self.marker_scale = marker_scale
        self.base_object.data.update()

    def get_geometry(self):
        return self._points.reshape(-1, 3), [], []

    @property
    def marker_scale(self):
        return self._marker_scale

    @marker_scale.setter
    def marker_scale(self, marker_scale):
        self._marker_scale = (
            np.array(marker_scale) if marker_scale is not None else marker_scale
        )
        self.update_marker_scale()

    def update_marker_scale(self):
        if self._marker_scale is not None:
            marker_scale, marker_dims = self.tile_data(
                self._marker_scale, [[3], []], "marker scale"
            )
            if marker_dims == []:
                marker_scale = np.array([marker_scale] * 3).T
            bu.set_vertex_attribute(
                self.mesh, Constants.MARKER_SCALE, marker_scale, "FLOAT_VECTOR"
            )

    @property
    def marker_rotation(self):
        return self._marker_rotation

    @marker_rotation.setter
    def marker_rotation(self, marker_rotation):
        self._marker_rotation = (
            np.array(marker_rotation)
            if marker_rotation is not None
            else marker_rotation
        )
        self.update_marker_rotation()

    def update_marker_rotation(self):
        if self._marker_rotation is not None:
            marker_rotation, rotation_dims = self.tile_data(
                self._marker_rotation, [[3], [3, 3]], "marker rotation"
            )
            if rotation_dims == [3, 3]:
                marker_rotation = np.stack(
                    [np.array(mu.Matrix(r).to_euler()) for r in marker_rotation]
                )
            bu.set_vertex_attribute(
                self.mesh, Constants.MARKER_ROTATION, marker_rotation, "FLOAT_VECTOR"
            )


def add_mesh_markers(
    base_modifier,
    marker_type,
    randomize_rotation=False,
    set_scale=False,
    n_frames=0,
    with_color=False,
    **marker_kwargs,
):
    """Create a geometry node modifier that instances a mesh on each vertex.
    Args:
        base_modifier: modifier to add markers to.
        marker_type: name of marker type (see MARKER_TYPES), or a blender mesh/object to use as marker
        randomize_rotation: if True each mesh instance will be given a random rotation (uniform euler angles)
        set_scale: if True use the MARKER_SCALE attribute to set the marker scale
        n_frames: number of frames to animate, no animation if set to 0.
        marker_kwargs: additional arguments for configuring markers
    """
    node_linker = bu.get_node_linker(base_modifier)
    node_linker.new_input_socket("Point Color", "NodeSocketMaterial")

    points_socket = node_linker.new_node(
        "GeometryNodeMeshToPoints", mesh=node_linker.group_input.outputs["Geometry"]
    ).outputs["Points"]

    if marker_type in Constants.MARKER_TYPES:
        # use one of the default marker types
        mesh_socket = node_linker.new_node(
            node_type=Constants.MARKER_TYPES[marker_type], **marker_kwargs
        ).outputs["Mesh"]
    elif isinstance(marker_type, (bpy.types.Object, bpy.types.Collection)):
        # use custom object or collection as marker
        subtype = marker_type.__class__.__name__
        node_linker.new_input_socket("Point Instance", f"NodeSocket{subtype}")
        base_modifier[node_linker.input_sockets["Point Instance"]] = marker_type
        mesh_socket = node_linker.new_node(
            f"GeometryNode{subtype}Info",
            **{subtype: node_linker.group_input.outputs["Point Instance"]},
        ).outputs[{"Object": "Geometry", "Collection": "Instances"}[subtype]]
        marker_type.hide_viewport = True
        marker_type.hide_render = True
    else:
        raise TypeError(
            f"Invalid marker type: {marker_type}, expected Object or Collection, "
            f"or one of: {', '.join(Constants.MARKER_TYPES)}"
        )

    if with_color:
        mesh_socket = node_linker.new_node(
            "GeometryNodeSetMaterial",
            geometry=mesh_socket,
            material=node_linker.group_input.outputs["Point Color"],
        ).outputs["Geometry"]

    marker_scale = node_linker.new_node(
        "GeometryNodeInputNamedAttribute",
        data_type="FLOAT_VECTOR",
        name=Constants.MARKER_SCALE,
    )
    marker_rotation = node_linker.new_node(
        "GeometryNodeInputNamedAttribute",
        data_type="FLOAT_VECTOR",
        name=Constants.MARKER_ROTATION,
    )
    instance_on_points_node = node_linker.new_node(
        "GeometryNodeInstanceOnPoints",
        points=points_socket,
        selection=(
            None
            if n_frames is None
            else bu.get_frame_selection_node(base_modifier, n_frames).outputs["Value"]
        ),
        instance=mesh_socket,
        rotation=marker_rotation.outputs["Attribute"],
        scale=marker_scale.outputs["Attribute"] if set_scale else [1, 1, 1],
    )
    if randomize_rotation:
        # these rotation are not uniform (some orientations will be more likely than others)
        # but it usually looks decent
        random_euler = node_linker.new_node("FunctionNodeRandomValue")
        random_euler.data_type = "FLOAT_VECTOR"
        random_euler.inputs["Max"].default_value = (180, 180, 180)
        node_linker.link(
            random_euler.outputs["Value"], instance_on_points_node.inputs["Rotation"]
        )

    realize_instances_node = node_linker.new_node(
        "GeometryNodeRealizeInstances",
        geometry=instance_on_points_node.outputs["Instances"],
    )
    node_linker.new_node(
        "NodeGroupOutput", geometry=realize_instances_node.outputs["Geometry"]
    )
    return node_linker


def add_sphere_markers(base_modifier, n_frames, **marker_kwargs):
    """Create a geometry node modifier that adds a point on each vertex. This will result in perfect spheres, only
        visible in rendered view with rendering engine set to `Cycles`
    Args:
        base_modifier: modifier to add sphere markers to.
        n_frames: number of frames to animate, no animation if set to 0.
        marker_kwargs: arguments to passed to node_linker.new_node when generating point node. e.g. radius=0.1
    """
    node_linker = bu.get_node_linker(base_modifier)
    node_linker.new_input_socket("Point Color", "NodeSocketMaterial")

    points = node_linker.new_node(
        "GeometryNodeMeshToPoints",
        mesh=node_linker.group_input.outputs["Geometry"],
        selection=(
            None
            if n_frames is None
            else bu.get_frame_selection_node(base_modifier, n_frames).outputs["Value"]
        ),
        **marker_kwargs,
    ).outputs["Points"]
    node = node_linker.new_node(
        "GeometryNodeSetMaterial",
        geometry=points,
        material=node_linker.group_input.outputs["Point Color"],
    )
    node_linker.new_node("NodeGroupOutput", geometry=node.outputs["Geometry"])
    return node_linker
