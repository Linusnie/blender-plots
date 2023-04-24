import numpy as np

import bpy
from blender_plots import plots_base
from blender_plots import blender_utils as bu


class Surface(plots_base.Plot):
    """Create a surface plot.

    Args:
        x,y,z:
            If y and z are not provided: expects x to be a MxNx3 array with xyz positions for points to plot as a surface, or TxMxNx3 for sequence of to animate
            if y and z are provided: expects x,y,z to have shapes MxN or TxMxN arrays for xyz coordinates respectively.
        color: MxNx3 or MxNx4 array or with RGB or RGBA values for each point, or a single RGB/RGBA-value (e.g. (1, 0, 0) for red) to apply to every point.
        name: name to use for blender object. Will delete any previous plot with the same name.
    """

    def __init__(self, x, y=None, z=None, color=None, name="surface"):
        super(Surface, self).__init__(x, y, z, color=color, name=name, n_dims=2)
        if self.n_frames is not None:
            animate(self.modifier, self.n_frames)

    @property
    def n_points_x(self):
        return self.dims[0]
    
    @property
    def n_points_y(self):
        return self.dims[1]

    def get_geometry(self):
        faces = get_faces(self.n_points_x, self.n_points_y, 1 if self.n_frames is None else self.n_frames)
        return self._points.reshape(-1, 3), [], faces.reshape(-1, 4)

    def tile_data(self, data_array, valid_dims, name=""):
        """Tile or reshape data_array with shape TxMxNx(dims), MxNx(dims) or (dims) to shape (T*M*N)x(dims)."""
        match data_array.shape:
            case (self.n_frames, self.n_points_x, self.n_points_y, *dims) if dims in valid_dims:
                out_array = data_array.reshape(self.n_frames * self.n_points, *dims)
            case (self.n_points_x, self.n_points_y, *dims) if dims in valid_dims:
                if self.n_frames is not None:
                    out_array = np.tile(data_array.reshape(-1, *dims), (self.n_frames, *([1] * len(dims))))
                else:
                    out_array = data_array.reshape(self.n_vertices, *dims)
            case (*dims, ) if dims in valid_dims:
                out_array = np.tile(data_array, (self.n_vertices, *([1]*len(dims))))
            case _:
                raise ValueError(
                    f"Invalid {name} data shape: {data_array.shape} with {self.n_frames=}, {self.n_points=}")
        return out_array, dims


def get_faces(n_points_x, n_points_y, n_frames):
    return np.array([
        [
            j * n_points_x * n_points_y +  np.array([i, i + 1, i + n_points_x + 1, i + n_points_x])
            for i in range(n_points_x * (n_points_y - 1))
            if (i + 1) % n_points_x != 0
        ]
        for j in range(n_frames)
    ])

def animate(base_modifier, n_frames):
    if base_modifier.node_group is None:
        base_modifier.node_group = bu.geometry_node_group_empty_new()
    node_linker = bu.NodeLinker(base_modifier.node_group)

    visible_geometry = node_linker.new_node(
        "GeometryNodeSeparateGeometry",
        geometry=node_linker.group_input.outputs["Geometry"],
        selection=bu.get_frame_selection_node(base_modifier, n_frames).outputs["Value"]
    ).outputs["Selection"]
    node_linker.new_node("NodeGroupOutput", geometry=visible_geometry)
