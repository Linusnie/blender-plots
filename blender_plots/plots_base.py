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
        self.modifier = self.base_object.modifiers.new(type="NODES", name=name)

        points, self.n_frames, *self.dims = get_points_array(x, y, z, n_dims)
        self.points = points
        self.color = color

    @property
    def n_points(self):
        return np.prod(self.dims)

    @property
    def n_vertices(self):
        return self.n_points * (1 if self.n_frames is None else self.n_frames)

    @property
    def points(self):
        return self._points

    def get_geometry(self):
        raise NotImplementedError

    @points.setter
    def points(self, points):
        if self._points is not None and points.shape != self._points.shape:
            raise ValueError(f"Can't change number of points: was {self._points.shape=}, got {self.points.shape=}")
        self._points = points
        self.update_points()

    def update_points(self):
        if len(self.mesh.vertices) == 0:
            vertices, edges, faces = self.get_geometry()
            self.mesh.from_pydata(vertices, edges, faces)
        elif len(self.mesh.vertices) == len(self._points.reshape(-1, 3)):
            self.mesh.vertices.foreach_set("co", self._points.reshape(-1))
        else:
            raise ValueError(f"Can't change number of vertices,"
                             f"was {len(self.mesh.vertices)=}, got {self._point.shape=}.")

        if self.n_frames is not None:
            bu.set_vertex_attribute(
                self.mesh, bu.Constants.FRAME_INDEX,
                np.arange(0, self.n_frames)[None].repeat(self.n_points, axis=1).reshape(-1)
            )

        self.base_object.data = self.mesh
        self.mesh.update()

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

    def tile_data(self, data_array, valid_dims, name=""):
        """Tile or reshape data_array with shape TxNx(dims), Nx(dims) or (dims) to shape (T*N)x(dims)."""
        if len(self.dims) != 1:
            raise NotImplementedError("Only 1D data can be tiled with base class.")

        match data_array.shape:
            case (self.n_frames, self.n_points, *dims) if dims in valid_dims:
                out_array = data_array.reshape(self.n_vertices, *dims)
            case (self.n_points, *dims) if dims in valid_dims:
                if self.n_frames is not None:
                    out_array = np.tile(data_array, (self.n_frames, *([1] * len(dims))))
                else:
                    out_array = data_array
            case (*dims, ) if dims in valid_dims:
                out_array = np.tile(data_array, (self.n_vertices, *([1]*len(dims))))
            case _:
                raise ValueError(
                    f"Invalid {name} data shape: {data_array.shape} with {self.n_frames=}, {self.n_points=}")
        return out_array, dims


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
