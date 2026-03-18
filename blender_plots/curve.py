import numpy as np

import blender_plots.blender_utils as bu
from blender_plots import plots_base


class Curve(plots_base.Plot):
    """Create a curve plot.

    Args:
        x, y, z:
            If y and z are not provided: expects x to be a Nx3 array with xyz positions for the curve,
                or TxNx3 for a sequence of curves to animate.
            If y and z are provided: expects x, y, z to be length N or TxN arrays for xyz coordinates respectively.
        color: (Tx)Nx3 or (Tx)Nx4 array with RGB or RGBA values for each point and (optionally) time,
            or a single RGB/RGBA value (e.g. (1, 0, 0) for red) to apply to every point.
        name: name to use for blender object. Will delete any previous plot with the same name.
        radius: radius of the rendered tube.
    """

    def __init__(self, x, y=None, z=None, color=None, name="curve", radius=0.1):
        super().__init__(x, y, z, color=color, name=name, n_dims=1)
        node_linker = setup_curve_nodes(
            self.modifier,
            n_frames=self.n_frames,
            radius=radius,
            with_color=color is not None,
        )
        if color is not None:
            self.modifier[node_linker.input_sockets["Curve Color"]] = self.color_material
        self.base_object.data.update()

    def get_geometry(self):
        N = self.dims[0]
        n_frames = 1 if self.n_frames is None else self.n_frames
        edges = np.array([
            [j * N + i, j * N + i + 1]
            for j in range(n_frames)
            for i in range(N - 1)
        ])
        return self._points.reshape(-1, 3), edges, []


def setup_curve_nodes(modifier, n_frames, radius=0.1, with_color=False):
    """Set up geometry nodes to render mesh edges as a tube."""
    node_linker = bu.get_node_linker(modifier)
    geometry = node_linker.group_input.outputs["Geometry"]

    if n_frames is not None:
        geometry = node_linker.new_node(
            "GeometryNodeSeparateGeometry",
            geometry=geometry,
            selection=bu.get_frame_selection_node(modifier, n_frames).outputs["Value"],
        ).outputs["Selection"]

    curve = node_linker.new_node(
        "GeometryNodeMeshToCurve",
        mesh=geometry,
    ).outputs["Curve"]

    profile = node_linker.new_node(
        "GeometryNodeCurvePrimitiveCircle",
        radius=radius,
    ).outputs["Curve"]

    tube = node_linker.new_node(
        "GeometryNodeCurveToMesh",
        curve=curve,
        profile_curve=profile,
    ).outputs["Mesh"]

    # Rounded caps: instance a sphere at the first and last point of each spline.
    # RealizeInstances propagates the marker_color from the instancing point to each
    # realized sphere, so per-point colors are preserved at the caps.
    endpoint_sel = node_linker.new_node(
        "GeometryNodeCurveEndpointSelection",
        start_size=1,
        end_size=1,
    )
    sphere = node_linker.new_node(
        "GeometryNodeMeshIcoSphere",
        radius=radius,
        subdivisions=3,
    )
    cap_instances = node_linker.new_node(
        "GeometryNodeInstanceOnPoints",
        points=curve,
        selection=endpoint_sel.outputs["Selection"],
        instance=sphere.outputs["Mesh"],
    ).outputs["Instances"]
    caps = node_linker.new_node(
        "GeometryNodeRealizeInstances",
        geometry=cap_instances,
    ).outputs["Geometry"]

    join_node = node_linker.new_node("GeometryNodeJoinGeometry", geometry=tube)
    node_linker.node_group.links.new(caps, join_node.inputs[0])
    out_geometry = join_node.outputs["Geometry"]

    if with_color:
        node_linker.new_input_socket("Curve Color", "NodeSocketMaterial")
        out_geometry = node_linker.new_node(
            "GeometryNodeSetMaterial",
            geometry=out_geometry,
            material=node_linker.group_input.outputs["Curve Color"],
        ).outputs["Geometry"]

    node_linker.new_node("NodeGroupOutput", geometry=out_geometry)
    return node_linker
