import numpy as np

import bpy
import bmesh
import blender_plots_tmp.blender_utils as bu

POINT_COLOR = "point_color"


class Scatter:
    """Create a scatterplot.

    Args:
        points: Nx3 array with xyz positions for points to scatter
        color: Nx3 array with rgb values for each point, or a single rgb-value (e.g. (1, 0, 0) for red) to apply to
            every point.
        name: name to use for blender object. Will delete any previous plot with the same name.
        point_type: select appearance of points. Options:
            "mesh" (str): will use **point_kwargs to instance geometry node that generates what to instance on each
                point.
            "spheres" (str): will generate a perfect sphere on each point.
                Only visible in rendered view with rendering engine set to `Cycles`
            Mesh or Object containing mesh: will instance the provided mesh on each point, overrides point_kwargs
        point_kwargs: if point_type is set to "mesh" or "spheres" and kwargs will be supplied to node_linker.new_node.
            See readme for examples.
    """

    def __init__(self, points, color=None, name="scatter", point_type="mesh",
                 randomize_rotation=False, **point_kwargs):
        self.name = name
        self.base_object = None
        self.mesh = None
        self.color_material = None

        self.points = points
        if point_type == "mesh":
            self.points_modifier = instance_mesh_on_points(self.base_object, randomize_rotation=randomize_rotation,
                                                           **point_kwargs)
        elif point_type == "spheres":
            self.points_modifier = add_spheres_to_points(self.base_object, **point_kwargs)
        elif isinstance(point_type, bpy.types.Mesh) or isinstance(point_type, bpy.types.Object):
            self.points_modifier = instance_mesh_on_points(self.base_object, mesh=point_type,
                                                           randomize_rotation=randomize_rotation)
        self.color = color

    @property
    def points(self):
        return self._points

    @points.setter
    def points(self, points):
        self._points = points
        self.update_points()

    def update_points(self):
        if self.mesh is None:
            self.mesh = bpy.data.meshes.new(self.name)
            self.mesh.from_pydata(self._points, [], [])
        else:
            self.mesh.vertices.foreach_set("co", self._points.reshape(-1))

        if self.base_object is None:
            self.base_object = bu.new_empty(self.name, self.mesh)
        else:
            self.base_object.data = self.mesh
        self.mesh.update()

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = color
        self.update_color()

    def update_color(self):
        if self._color is not None:
            set_vertex_colors(self.mesh, self.color)
            self.color_material = get_vertex_color_material()
            self.mesh.materials.append(self.color_material)
            self.points_modifier["Input_2"] = self.color_material


def set_vertex_colors(mesh, color):
    """Add a point_color attribute to each vertex in the mesh with values given by `color`"""
    if np.array(color).ndim == 1:
        color = np.tile(color, (len(mesh.vertices), 1))
    if color.shape[1] == 3:
        color = np.hstack([color, np.ones((len(color), 1))])
    elif not color.shape[1] == 4:
        raise ValueError(f"Invalid color array shape {color.shape}, expectex Nx3 or Nx4")
    if len(mesh.vertices) != len(color):
        raise ValueError(f"Got {len(mesh.vertices)} vertices and {len(color)} color values")

    if POINT_COLOR not in mesh.attributes:
        mesh.attributes.new(name=POINT_COLOR, type="FLOAT_COLOR", domain="POINT")
    mesh.attributes[POINT_COLOR].data.foreach_set("color", color.reshape(-1))


def get_vertex_color_material():
    """Create a material that obtains its color from the point_color attribute"""
    material = bpy.data.materials.new("color")
    material.use_nodes = True
    color_node = material.node_tree.nodes.new("ShaderNodeAttribute")
    color_node.attribute_name = POINT_COLOR

    material.node_tree.links.new(color_node.outputs["Color"],
                                 material.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    return material


def instance_mesh_on_points(base_object, mesh=None, randomize_rotation=False, **mesh_kwargs):
    """Create a geometry node modifier that instances a mesh on each vertex.
    Args:
        base_object: object containing mesh with vertices to instance on.
        mesh: mesh or object containing mesh to instance on points, overrides mesh_kwargs if supplied
        randomize_rotation: if True each mesh instance will be given a random rotation (uniform euler angles)
        mesh_kwargs: arguments to passed to node_linker.new_node to generate point mesh. See NodeLinker and examples in
         readme
    """
    modifier = base_object.modifiers.new(type="NODES", name="spheres")
    node_linker = bu.NodeLinker(modifier.node_group)
    modifier.node_group.inputs.new("NodeSocketMaterial", "Point Color")  # Input_2

    points_socket = node_linker.new_node(
        "GeometryNodeMeshToPoints",
        mesh=node_linker.group_input.outputs["Geometry"]
    ).outputs["Points"]

    if mesh is None:
        # use kwargs to generate a node (typically mesh primitive)
        if "node_type" not in mesh_kwargs:
            mesh_kwargs["node_type"] = "GeometryNodeMeshCube"
        mesh_socket = node_linker.new_node(**mesh_kwargs).outputs["Mesh"]
    elif isinstance(mesh, bpy.types.Mesh) or isinstance(mesh, bpy.types.Object):
        # use the supplied mesh by adding it as an input socket to the modifier
        modifier.node_group.inputs.new("NodeSocketObject", "Point Instance")  # Input_3
        modifier["Input_3"] = mesh
        modifier.show_viewport = False
        modifier.show_viewport = True
        mesh_socket = node_linker.new_node(
            "GeometryNodeObjectInfo",
            Object=node_linker.group_input.outputs["Point Instance"]
        ).outputs["Geometry"]
    else:
        raise TypeError(f"Invalid mesh: {mesh}")

    colored_mesh = node_linker.new_node(
        "GeometryNodeSetMaterial",
        geometry=mesh_socket,
        material=node_linker.group_input.outputs["Point Color"]
    ).outputs["Geometry"]
    node = node_linker.new_node(
        "GeometryNodeInstanceOnPoints",
        points=points_socket,
        instance=colored_mesh
    )
    if randomize_rotation:
        # these rotation are not uniform (some orientations will be more likely than others)
        # but it usually looks decent
        random_euler = node_linker.new_node("FunctionNodeRandomValue", max=(180, 180, 180))
        random_euler.data_type = "FLOAT_VECTOR"
        node_linker.link(random_euler.outputs["Value"], node.inputs["Rotation"])

    node = node_linker.new_node("GeometryNodeRealizeInstances", geometry=node.outputs["Instances"])
    node_linker.new_node("NodeGroupOutput", geometry=node.outputs["Geometry"])
    return modifier


def add_spheres_to_points(base_object, **point_kwargs):
    """Create a geometry node modifier that adds a point on each vertex. This will result in perfect spheres, only
        visible in rendered view with rendering engine set to `Cycles`
    Args:
        base_object: object containing mesh with vertices to instance on.
        point_kwargs: arguments to passed to node_linker.new_node when generating point node. e.g. radius=0.1
    """
    modifier = base_object.modifiers.new(type="NODES", name="spheres")
    node_linker = bu.NodeLinker(modifier.node_group)
    modifier.node_group.inputs.new("NodeSocketMaterial", "Point Color")  # Input_2

    points = node_linker.new_node(
        "GeometryNodeMeshToPoints",
        mesh=node_linker.group_input.outputs["Geometry"],
        **point_kwargs,
    ).outputs["Points"]
    node = node_linker.new_node(
        "GeometryNodeSetMaterial",
        geometry=points,
        material=node_linker.group_input.outputs["Point Color"]
    )
    node_linker.new_node("NodeGroupOutput", geometry=node.outputs["Geometry"])
    return modifier
