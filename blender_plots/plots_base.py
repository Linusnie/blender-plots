import numpy as np

import bpy
from blender_plots import blender_utils as bu


class Plot:
    def __init__(self, x, y, z, color=None, name="plot", n_dims=1):
        self.name = name
        self.mesh = bpy.data.meshes.new(self.name)
        self.base_object = bu.new_empty(self.name, self.mesh)
        self.color_material = None
        self.color_material = None
        self._points = None

        points, self.n_frames, *self.dims = get_points_array(x, y, z, n_dims)
        self.points = points
        self.color = color

    @property
    def points(self):
        return self._points

    @points.setter
    def points(self, points):
        if self._points is not None and points.shape != self._points.shape:
            raise ValueError(f"Can't change number of points: was {self._points.shape=}, got {self.points.shape=}")
        self._points = points
        self.update_points()

    def update_points(self):
        raise NotImplementedError

    @property
    def color(self):
        return self._color

    @color.setter
    def color(self, color):
        self._color = np.array(color) if color is not None else color
        self.update_color()

    def update_color(self):
        if self._color is not None:
            color, _ = self.tile_data(self._color, [[3], [4]], "color")
            bu.set_vertex_colors(self.mesh, color)
            self.color_material = bu.get_vertex_color_material()
            self.mesh.materials.append(self.color_material)


def get_points_array(x, y, z, n_dims=1):
    """Parses x,y,z to a N1xN2x...xN{n_dims}x3 or TxN1xN2x...xN{n_dims}x3 array of points."""
    if (y is None) and (z is None):
        # only x provided, parse it as Nx3 or TxNx3
        x = np.array(x)
        match x.shape:
            case (3, ):
                points = x.reshape(1, 1, 3)
                n_frames = None
                dims = (1 for _ in range(n_dims))
            case (*dims, 3, ) if len(dims) == n_dims:
                points = x
                n_frames = None
            case (n_frames, *dims, 3, ) if len(dims) == n_dims:
                points = x
            case _:
                dims_str = 'x'.join(f'N{i + 1}' for i in range(n_dims))
                raise ValueError(f"Invalid shape for points: {x.shape=}, expected {dims_str}x3 or Tx{dims_str}x3")    
    elif (y is not None) and (z is not None):
        # parse x,y,z as N,N,N or TxN,TxN,TxN
        x, y, z = np.array(x), np.array(y), np.array(z)
        match x.shape, y.shape, z.shape:
            case (), (), ():
                points = np.array([x, y, z]).reshape(1, 3)
                n_frames, dims = None, (1 for _ in range(n_dims))
            case (*dims_x, ), (*dims_y, ), (*dims_z, ) if (dims_x == dims_y == dims_z) and len(dims_x) == n_dims:
                points = np.stack([x, y, z], axis=-1)
                n_frames, dims = None, dims_x
            case (tx, *dims_x), (ty, *dims_y), (tz, *dims_z) if (tx == ty == tz) and (dims_x == dims_y == dims_z) and len(dims_x) == n_dims:
                points = np.stack([x, y, z], axis=-1)
                n_frames, dims = tx, dims_x
            case _:
                raise ValueError(f"Incompatible shapes: {x.shape=}, {y.shape=}, {z.shape=}")

    else:
        raise ValueError(f"Eiter both y and z needs to be provided, or neither")
    return points, n_frames, *dims
