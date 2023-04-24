from dataclasses import dataclass
import numpy as np
import numbers

import bpy
import mathutils as mu
import blender_plots.blender_utils as bu
from blender_plots import plots_base



@dataclass
class Constants:
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
        color: Nx3 or Nx4 array or with RGB or RGBA values for each point, or a single RGB/RGBA-value
            (e.g. (1, 0, 0) for red) to apply to every point.
        name: name to use for blender object. Will delete any previous plot with the same name.
        marker_type: select appearance of points. Either MARKER_TYPE, "spheres", bpy_types.Mesh or bpy_types.Object
        marker_scale: xyz scale for markers
        marker_rotation: Nx3 (euler angles in radians) or Nx3x3 (rotation matrices) array specifying the rotation for
            each marker. Or "random" for applying a random rotation to each marker.
        randomize_rotation: If set to True randomize the rotation of each marker. Overrides marker_rotation.
        marker_kwargs: additional arguments for configuring markers
    """

    def __init__(self, x, y=None, z=None, color=None, name="scatter", marker_type="cubes", marker_scale=None,
                 marker_rotation=None, randomize_rotation=False, **marker_kwargs):
        super(Scatter, self).__init__(x, y, z, color=color, name=name, n_dims=1)

        self.marker_modifier = self.base_object.modifiers.new(type="NODES", name="spheres")
        if marker_type == "spheres":
            add_sphere_markers(self.marker_modifier, n_frames=self.n_frames, **marker_kwargs)
        elif marker_type is not None:
            add_mesh_markers(
                self.marker_modifier,
                randomize_rotation=randomize_rotation,
                marker_type=marker_type,
                marker_scale=marker_scale,
                n_frames=self.n_frames,
                **marker_kwargs
            )
        self.marker_modifier["Input_2"] = self.color_material
        self.marker_rotation = marker_rotation

    @property
    def n_points(self):
        return self.dims[0]

    def update_points(self):
        if len(self.mesh.vertices) == 0:
            self.mesh.from_pydata(self._points.reshape(-1, 3), [], [])
        elif len(self.mesh.vertices) == len(self._points):
            self.mesh.vertices.foreach_set("co", self._points.reshape(-1))

        if self.n_frames is not None:
            bu.set_vertex_attribute(
                self.mesh, bu.Constants.FRAME_INDEX,
                np.arange(0, self.n_frames)[None].repeat(self.n_points, axis=1).reshape(-1)
            )

        self.base_object.data = self.mesh
        self.mesh.update()

    @property
    def marker_rotation(self):
        return self._marker_rotation

    @marker_rotation.setter
    def marker_rotation(self, marker_rotation):
        self._marker_rotation = np.array(marker_rotation) if marker_rotation is not None else marker_rotation
        self.update_marker_rotation()

    def update_marker_rotation(self):
        if self._marker_rotation is not None:
            marker_rotation, rotation_dims = self.tile_data(self._marker_rotation, [[3], [3, 3]], "marker rotation")
            if rotation_dims == [3, 3]:
                marker_rotation = np.stack([np.array(mu.Matrix(r).to_euler()) for r in marker_rotation])
            bu.set_vertex_attribute(self.mesh, Constants.MARKER_ROTATION, marker_rotation, "FLOAT_VECTOR")

    def tile_data(self, data_array, valid_dims, name=""):
        """Tile or reshape data_array with shape NxTx(dims), Nx(dims) or (dims) to shape (N*T)x(dims)."""
        match data_array.shape:
            case (self.n_frames, self.n_points, *dims) if dims in valid_dims:
                out_array = data_array.reshape(self.n_frames * self.n_points, *dims)
            case (self.n_points, *dims) if dims in valid_dims:
                if self.n_frames is not None:
                    out_array = np.tile(data_array, (self.n_frames, *([1] * len(dims))))
                else:
                    out_array = data_array
            case (*dims, ) if dims in valid_dims:
                n_points_total = self.n_points * (1 if self.n_frames is None else self.n_frames)
                out_array = np.tile(data_array, (n_points_total, *([1]*len(dims))))
            case _:
                raise ValueError(
                    f"Invalid {name} data shape: {data_array.shape} with {self.n_frames=}, {self.n_points=}")
        return out_array, dims


def add_mesh_markers(base_modifier, marker_type, randomize_rotation=False, marker_scale=None,
                     n_frames=0, **marker_kwargs):
    """Create a geometry node modifier that instances a mesh on each vertex.
    Args:
        base_modifier: modifier to add markers to.
        marker_type: name of marker type (see MARKER_TYPES), or a blender mesh/object to use as marker
        randomize_rotation: if True each mesh instance will be given a random rotation (uniform euler angles)
        marker_scale: xyz scale for markers
        n_frames: number of frames to animate, no animation if set to 0.
        marker_kwargs: additional arguments for configuring markers
    """
    if base_modifier.node_group is None:
        base_modifier.node_group = bu.geometry_node_group_empty_new()
    node_linker = bu.NodeLinker(base_modifier.node_group)

    # create all inputs, some might be unused depending on input parameters.
    # order is important since keys are generically created in numerical order.
    base_modifier.node_group.inputs.new("NodeSocketMaterial", "Point Color")  # Input_2
    base_modifier.node_group.inputs.new("NodeSocketObject", "Point Instance")  # Input_3

    points_socket = node_linker.new_node(
        "GeometryNodeMeshToPoints",
        mesh=node_linker.group_input.outputs["Geometry"]
    ).outputs["Points"]

    if marker_type in Constants.MARKER_TYPES:
        mesh_socket = node_linker.new_node(node_type=Constants.MARKER_TYPES[marker_type], **marker_kwargs).outputs["Mesh"]
    elif isinstance(marker_type, bpy.types.Mesh) or isinstance(marker_type, bpy.types.Object):
        # use the supplied mesh by adding it as an input socket to the base_modifier
        base_modifier["Input_3"] = marker_type
        base_modifier.show_viewport = False
        base_modifier.show_viewport = True
        mesh_socket = node_linker.new_node(
            "GeometryNodeObjectInfo",
            Object=node_linker.group_input.outputs["Point Instance"]
        ).outputs["Geometry"]
        marker_type.hide_viewport = True
        marker_type.hide_render = True
    else:
        raise TypeError(f"Invalid marker type: {marker_type}, expected bpy.types.Mesh, bpy.Types.Object, "
                        f"or one of: {', '.join(Constants.MARKER_TYPES)}")

    colored_mesh = node_linker.new_node(
        "GeometryNodeSetMaterial",
        geometry=mesh_socket,
        material=node_linker.group_input.outputs["Point Color"]
    ).outputs["Geometry"]

    if marker_scale is not None and np.array(marker_scale).shape == ():
        marker_scale = [marker_scale] * 3

    marker_rotation = node_linker.new_node(
        "GeometryNodeInputNamedAttribute",
        data_type="FLOAT_VECTOR",
        name=Constants.MARKER_ROTATION,
    )
    instance_on_points_node = node_linker.new_node(
        "GeometryNodeInstanceOnPoints",
        points=points_socket,
        selection=None if n_frames is None else get_frame_selection_node(base_modifier, n_frames).outputs["Value"],
        instance=colored_mesh,
        rotation=marker_rotation.outputs["Attribute"],
        scale=marker_scale,
    )
    if randomize_rotation:
        # these rotation are not uniform (some orientations will be more likely than others)
        # but it usually looks decent
        random_euler = node_linker.new_node("FunctionNodeRandomValue", max=(180, 180, 180))
        random_euler.data_type = "FLOAT_VECTOR"
        node_linker.link(random_euler.outputs["Value"], instance_on_points_node.inputs["Rotation"])

    realize_instances_node = node_linker.new_node(
        "GeometryNodeRealizeInstances",
        geometry=instance_on_points_node.outputs["Instances"]
    )
    node_linker.new_node("NodeGroupOutput", geometry=realize_instances_node.outputs["Geometry"])


def add_sphere_markers(base_modifier, n_frames, **marker_kwargs):
    """Create a geometry node modifier that adds a point on each vertex. This will result in perfect spheres, only
        visible in rendered view with rendering engine set to `Cycles`
    Args:
        base_modifier: modifier to add sphere markers to.
        n_frames: number of frames to animate, no animation if set to 0.
        marker_kwargs: arguments to passed to node_linker.new_node when generating point node. e.g. radius=0.1
    """
    if base_modifier.node_group is None:
        base_modifier.node_group = bu.geometry_node_group_empty_new()
    node_linker = bu.NodeLinker(base_modifier.node_group)

    base_modifier.node_group.inputs.new("NodeSocketMaterial", "Point Color")  # Input_2

    points = node_linker.new_node(
        "GeometryNodeMeshToPoints",
        mesh=node_linker.group_input.outputs["Geometry"],
        selection=None if n_frames is None else get_frame_selection_node(base_modifier, n_frames).outputs["Value"],
        **marker_kwargs,
    ).outputs["Points"]
    node = node_linker.new_node(
        "GeometryNodeSetMaterial",
        geometry=points,
        material=node_linker.group_input.outputs["Point Color"]
    )
    node_linker.new_node("NodeGroupOutput", geometry=node.outputs["Geometry"])


def get_frame_selection_node(modifier, n_frames):
    """Add node that filters points based on the Frame Index property."""
    node_linker = bu.NodeLinker(modifier.node_group)
    frame_index = node_linker.new_node(
        "GeometryNodeInputNamedAttribute",
        data_type="FLOAT",
        name=bu.Constants.FRAME_INDEX,
    )
    frame_selection_node = node_linker.new_node(
        "ShaderNodeMath",
        operation="COMPARE",
        input_1=frame_index.outputs[1],
        input_2=0.5
    )

    action = bpy.data.actions.new("AnimationAction")
    fcurve = action.fcurves.new(data_path='nodes["Math"].inputs[0].default_value', index=0)
    fcurve.keyframe_points.add(2)
    fcurve.keyframe_points.foreach_set("co", [0, 0, n_frames, n_frames])
    bpy.context.scene.frame_end = n_frames - 1

    modifier.node_group.animation_data_create()
    modifier.node_group.animation_data.action = action

    return frame_selection_node
