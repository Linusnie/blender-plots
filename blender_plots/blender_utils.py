from dataclasses import dataclass
import numpy as np

import bpy


@dataclass
class Constants:
    MARKER_COLOR = "marker_color"
    FRAME_INDEX = "frame_index"
    ARROWS = "arrows"


class NodeLinker:
    """Wrapper for bpy.types.GeometryNodeTree which simplifies creating large node trees."""

    def __init__(self, node_group):
        self.node_group = node_group
        # blender creates socket names based on order they are created, so we keep a mapping from user-provided socket name to internal name
        self.input_sockets = {}

    def new_node(self, node_type, **kwargs):
        """Adds a new node to the node group

        Args:
            node_type: type of node to add (e.g. GeometryNodeInstanceOnPoints) - to find available names you can either
                hover over the node name when adding one through the node editor, or check the `bl_idname`
                property of a node in python.
            kwargs: arguments in one of the following forms:
                input_socket_name=node_socket: will connect the supplied node_socket to the input socket
                    (e.g. mesh=node_group["Group Input"].outputs["Geometry"] for GeometryNodeMeshToPoints)
                input_socket_name=value: set the value of input socket (e.g. size=(5, 1, 1) for GeometryNodeMeshCube).
                input_i=value: set input i of node to value, useful in case multiple inputs have the same name.
        """
        if node_type == "NodeGroupOutput":
            # can only have one group output
            node = self.node_group.nodes["Group Output"]
        else:
            node = self.node_group.nodes.new(node_type)

        for key, value in kwargs.items():
            if value is not None:
                match key.split("_"):
                    case ["input", i] if i.isdigit():
                        blender_key = int(i)
                    case _:
                        blender_key = python_arg_to_blender_key(key)
                if isinstance(value, bpy.types.NodeSocket):
                    self.link(value, node.inputs[blender_key])
                elif (isinstance(blender_key, int) or blender_key in node.inputs) and hasattr(node.inputs[blender_key], "default_value"):
                    node.inputs[blender_key].default_value = value # TODO: make sure this is done first, as it resets everything else
                elif hasattr(node, key):
                    setattr(node, key, value)
                else:
                    raise ValueError(f"Node {node} has no attribute {key} or input {blender_key}.")
        return node

    def link(self, from_socket, to_socket):
        self.node_group.links.new(from_socket, to_socket)

    def new_input(self, input_type, input_name):
        self.node_group.inputs.new(input_type, input_name)

    def new_input_socket(self, name, socket_type):
        if bpy.app.version[0] >= 4: # node group input/output interface changed in 4.0
            self.node_group.interface.new_socket(name, socket_type=socket_type)
        else:
            self.node_group.inputs.new(socket_type, name)
        socket_index = len(self.input_sockets) + 2 # starts at 2
        self.input_sockets[name] = socket_input_key(socket_index)

    @property
    def group_input(self):
        """Add input which can be accessed through modifiers panel."""
        return self.node_group.nodes["Group Input"]


def delete(obj, with_children=False):
    """Delete blender object and its children"""
    if with_children:
        for child in obj.children:
            delete(child, with_children=True)
    if isinstance(obj, bpy.types.Object):
        bpy.data.objects.remove(obj, do_unlink=True)
    elif isinstance(obj, bpy.types.Collection):
        bpy.data.collections.remove(obj, do_unlink=True)
    else:
        raise ValueError(f'Failed to delete object {obj}: unrecognized type')

def new_collection(name):
    if name in bpy.data.collections:
        delete(bpy.data.collections[name], with_children=True)
    collection = bpy.data.collections.new(name)
    bpy.context.collection.children.link(collection)
    return collection

def new_empty(name, object_data=None, select=True, collection=None):
    """Create new empty blender object with specified name and data, deletes any previous object with the same name."""
    if name in bpy.data.objects:
        delete(bpy.data.objects[name], with_children=True)

    new_object = bpy.data.objects.new(name, object_data)
    if collection is None:
        collection = bpy.context.collection
    collection.objects.link(new_object)

    if select:
        bpy.context.view_layer.objects.active = new_object

    return new_object


def add_modifier(base_object, modifier_type, **kwargs):
    modifier = base_object.modifiers.new(name=modifier_type.lower(), type=modifier_type)
    for key, value in kwargs.items():
        setattr(modifier, key, value)
    return modifier


def set_vertex_attribute(mesh, attribute_name,  attribute_values, attribute_type="FLOAT"):
    if attribute_name not in mesh.attributes:
        mesh.attributes.new(name=attribute_name, type=attribute_type, domain="POINT")
    data_type = "vector" if attribute_type == "FLOAT_VECTOR" else "value"
    mesh.attributes[attribute_name].data.foreach_set(data_type, attribute_values.reshape(-1))


def python_arg_to_blender_key(arg):
    """convert python argument to geometry node name, e.g. radius->Radius, instance_index->Instance Index"""
    return ' '.join([s.capitalize() for s in arg.split('_')])

def socket_input_key(i):
    return ('Socket_' if bpy.app.version[0] >= 4 else 'Input_') + f'{i}'

# From https://developer.blender.org/diffusion/B/browse/master/release/scripts/startup/bl_operators/geometry_nodes.py$7
def get_node_linker(modifier):
    if modifier.node_group is not None:
        return NodeLinker(modifier.node_group)
    group = bpy.data.node_groups.new("Geometry Nodes", 'GeometryNodeTree')
    if bpy.app.version[0] >= 4: # node group input/output interface changed in 4.0
        input_node = group.nodes.new('NodeGroupInput')
        output_node = group.nodes.new('NodeGroupOutput')
        group.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
        group.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        """Create new node group, useful in blender 3.2 since node group is not added to node modifiers by default."""
        group.inputs.new('NodeSocketGeometry', "Geometry")
        group.outputs.new('NodeSocketGeometry', "Geometry")
        input_node = group.nodes.new('NodeGroupInput')
        output_node = group.nodes.new('NodeGroupOutput')
    output_node.is_active_output = True

    input_node.select = False
    output_node.select = False

    input_node.location.x = -200 - input_node.width
    output_node.location.x = 200

    group.links.new(output_node.inputs[0], input_node.outputs[0])
    modifier.node_group = group
    return NodeLinker(modifier.node_group)

def set_vertex_colors(mesh, color):
    """Add a marker_color attribute to each vertex in `mesh` with values from (n_vertices)x(3 or 4) array `color`"""
    if color.shape[1] == 3:
        color = np.hstack([color, np.ones((len(color), 1))])
    elif not color.shape[1] == 4:
        raise ValueError(f"Invalid color array shape {color.shape}, expected Nx3 or Nx4")
    if len(mesh.vertices) != len(color):
        raise ValueError(f"Got {len(mesh.vertices)} vertices and {len(color)} color values")

    if Constants.MARKER_COLOR not in mesh.attributes:
        mesh.attributes.new(name=Constants.MARKER_COLOR, type="FLOAT_COLOR", domain="POINT")
    mesh.attributes[Constants.MARKER_COLOR].data.foreach_set("color", color.reshape(-1))


def get_vertex_color_material():
    """Create a material that obtains its color from the marker_color attribute"""
    material = bpy.data.materials.new("color")
    material.use_nodes = True
    color_node = material.node_tree.nodes.new("ShaderNodeAttribute")
    color_node.attribute_name = Constants.MARKER_COLOR

    material.node_tree.links.new(color_node.outputs["Color"],
                                 material.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    return material

def add_mesh_color(mesh, color):
    """Add uniform color to mesh."""
    if len(color) == 3:
        color = (*color, 1)
    material = bpy.data.materials.new("color")
    material.diffuse_color = color
    mesh.materials.append(material)

def get_frame_selection_node(modifier, n_frames):
    """Add node that filters points based on the Frame Index property."""
    node_linker = NodeLinker(modifier.node_group)
    frame_index = node_linker.new_node(
        "GeometryNodeInputNamedAttribute",
        data_type="FLOAT",
        name=Constants.FRAME_INDEX,
    )
    frame_selection_node = node_linker.new_node(
        "ShaderNodeMath",
        operation="COMPARE",
        input_1=frame_index.outputs[1],
        input_2=0.5
    )

    # link compare node to frame index
    action = bpy.data.actions.new("AnimationAction")
    fcurve = action.fcurves.new(data_path=f'nodes["{frame_selection_node.name}"].inputs[0].default_value', index=0)
    fcurve.keyframe_points.add(2)
    fcurve.keyframe_points.foreach_set("co", [0, 0, n_frames, n_frames])
    bpy.context.scene.frame_end = n_frames - 1

    modifier.node_group.animation_data_create()
    modifier.node_group.animation_data.action = action

    return frame_selection_node
