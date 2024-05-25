import numpy as np

from blender_plots import blender_utils as bu
from blender_plots import plots_base, scatter


class Arrows(plots_base.Plot):
    """Create an arrow plot.

    Args:
        start: xyz coordinate(s) of arrow starts (3, Nx3 or TxNx3 array - see scatter.py)
        vector: xyz components of arrow vectors, same size as `start`
        end: xyz coordinate(s) of arrow ends (can be provided instead of `vector`)
        color: (Tx)Nx3 or (Tx)Nx4 array or with RGB or RGBA values for each point and (optionally) time,
            or a single RGB/RGBA-value (e.g. (1, 0, 0) for red) to apply to every point.
        name: name to use for blender object. Will delete any previous plot with the same name.
        head_length: length of the arrow head.
        radius: radius of the arrow stem.
        radius_ratio: ratio of the arrow head radius to the stem radius.
        end_trim_length: length by which to reduce each arrow. If set to 0 the arrow tip will be exactly at `start`+`vector` (or `end` if provided)
    """

    def __init__(
        self,
        start,
        vector=None,
        end=None,
        color=None,
        name="arrows",
        head_length=1,
        radius=1,
        radius_ratio=1.5,
        end_trim_length=0,
    ):
        super(Arrows, self).__init__(
            start, None, None, color=color, name=name, n_dims=1
        )

        self.node_linker = add_arrows(
            self.modifier,
            self.n_frames,
            head_length,
            radius,
            radius_ratio,
            end_trim_length,
        )

        self.modifier[self.node_linker.input_sockets["Point Color"]] = (
            self.color_material
        )

        if (end is not None) and (vector is not None):
            raise ValueError(
                "Cannot provide both 'end' and 'vector' as input arguments."
            )
        elif end is not None:
            self.arrows = end - start
        else:
            self.arrows = vector
        self.base_object.data.update()

    def get_geometry(self):
        return self._points.reshape(-1, 3), [], []

    @property
    def arrows(self):
        return self._arrows

    @arrows.setter
    def arrows(self, arrows):
        self._arrows = np.array(arrows) if arrows is not None else arrows
        self.update_arrows()

    def update_arrows(self):
        if self._arrows is not None:
            arrows, marker_dims = self.tile_data(
                self._arrows, [[3], []], "marker scale"
            )
            if marker_dims == []:
                arrows = np.array([arrows] * 3).T
            bu.set_vertex_attribute(
                self.mesh, bu.Constants.ARROWS, arrows, "FLOAT_VECTOR"
            )


def add_arrows(
    base_modifier, n_frames, head_length, radius, radius_ratio, end_trim_length
):
    """ """
    node_linker = bu.get_node_linker(base_modifier)
    node_linker.new_input_socket("Point Color", "NodeSocketMaterial")
    if n_frames is None:
        frame_selection = None
    else:
        frame_selection = bu.get_frame_selection_node(base_modifier, n_frames).outputs[
            "Value"
        ]

    points_socket = node_linker.new_node(
        "GeometryNodeMeshToPoints", mesh=node_linker.group_input.outputs["Geometry"]
    ).outputs["Points"]

    arrows = node_linker.new_node(
        "GeometryNodeInputNamedAttribute",
        data_type="FLOAT_VECTOR",
        name=bu.Constants.ARROWS,
    ).outputs["Attribute"]
    lengths = node_linker.new_node(
        "ShaderNodeVectorMath", operation="LENGTH", vector=arrows
    ).outputs["Value"]
    lengths = node_linker.new_node(
        "ShaderNodeMath",
        operation="SUBTRACT",
        input_0=lengths,
        input_1=head_length + end_trim_length,
    ).outputs["Value"]
    rotations = node_linker.new_node(
        "FunctionNodeAlignEulerToVector", axis="Z", vector=arrows
    ).outputs["Rotation"]

    cylinder_mesh = node_linker.new_node(
        "GeometryNodeMeshCylinder", depth=1, radius=radius
    ).outputs["Mesh"]
    cylinder_mesh = node_linker.new_node(
        "GeometryNodeTransform", geometry=cylinder_mesh, translation=[0, 0, 0.5]
    ).outputs["Geometry"]
    colored_cylinder = node_linker.new_node(
        "GeometryNodeSetMaterial",
        geometry=cylinder_mesh,
        material=node_linker.group_input.outputs["Point Color"],
    ).outputs["Geometry"]
    cylinder_instances = node_linker.new_node(
        "GeometryNodeInstanceOnPoints",
        points=points_socket,
        selection=frame_selection,
        instance=colored_cylinder,
        rotation=rotations,
        scale=node_linker.new_node("ShaderNodeCombineXYZ", x=1, y=1, z=lengths).outputs[
            "Vector"
        ],
    ).outputs["Instances"]
    cylinder_geometry = node_linker.new_node(
        "GeometryNodeRealizeInstances", geometry=cylinder_instances
    ).outputs["Geometry"]

    cone_mesh = node_linker.new_node(
        "GeometryNodeMeshCone", depth=head_length, radius_bottom=radius * radius_ratio
    ).outputs["Mesh"]
    colored_cone = node_linker.new_node(
        "GeometryNodeSetMaterial",
        geometry=cone_mesh,
        material=node_linker.group_input.outputs["Point Color"],
    ).outputs["Geometry"]
    cone_instances = node_linker.new_node(
        "GeometryNodeInstanceOnPoints",
        points=points_socket,
        selection=frame_selection,
        instance=colored_cone,
        rotation=rotations,
    ).outputs["Instances"]
    cone_instances = node_linker.new_node(
        "GeometryNodeTranslateInstances",
        instances=cone_instances,
        translation=node_linker.new_node(
            "ShaderNodeCombineXYZ", x=0, y=0, z=lengths
        ).outputs["Vector"],
    ).outputs["Instances"]
    cone_geometry = node_linker.new_node(
        "GeometryNodeRealizeInstances", geometry=cone_instances
    ).outputs["Geometry"]
    arrow_geometry_node = node_linker.new_node(
        "GeometryNodeJoinGeometry", geometry=cylinder_geometry
    )
    node_linker.node_group.links.new(cone_geometry, arrow_geometry_node.inputs[0])

    node_linker.new_node(
        "NodeGroupOutput", geometry=arrow_geometry_node.outputs["Geometry"]
    )
    return node_linker
