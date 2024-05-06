import numpy as np
import bpy

from blender_plots import blender_utils as bu

def get_frustum(
        intrinsics,
        height,
        width,
        image_depth,
        name="",
        with_fill=True,
        thickness=0.03,
        color=None,
        color_fill=None,
    ):
    frustum_points = np.array([
        [0, height, 1],
        [width, height, 1],
        [0, 0, 1],
        [width, 0, 1]
    ]) * image_depth

    frustum_points = np.einsum('ij,...j->...i',
        np.linalg.inv(intrinsics),
        frustum_points,
    )
    frustum_edges = np.array([
        [0, 1],
        [1, 3],
        [3, 2],
        [2, 0],
        [0, 4],
        [1, 4],
        [2, 4],
        [3, 4]
    ])

    frustum_faces = [
        [0, 1, 4],
        [1, 3, 4],
        [3, 2, 4],
        [2, 0, 4],
    ]

    collection = bu.new_collection(name) if with_fill else None
    mesh = bpy.data.meshes.new("frustum")
    mesh.from_pydata(np.vstack([frustum_points, np.zeros(3)]), frustum_edges, frustum_faces)

    frustum = bu.new_empty(f"{name}_frustum", mesh, collection=collection)
    modifier = bu.add_modifier(frustum, "WIREFRAME", use_crease=True, crease_weight=0.6, thickness=thickness, use_boundary=True)
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    if color is not None:
        bu.add_mesh_color(frustum.data, color)

    if with_fill:
        mesh_fill = bpy.data.meshes.new("fill")
        mesh_fill.from_pydata(
            np.vstack([frustum_points, np.zeros(3)]),
            frustum_edges,
            frustum_faces + [[0, 1, 3, 2]]
        )
        bu.new_empty(f"{name}_fill", mesh_fill, collection=collection)
        if color_fill is not None:
            bu.add_mesh_color(mesh_fill, color_fill)
        elif color is not None:
            bu.add_mesh_color(mesh_fill, color)
        return collection
    else:
        return frustum

def get_rotaitons_facing_point(origin, points):
    n_points = len(points)
    d = (origin - points) / np.linalg.norm(origin - points, axis=-1)[:, None]
    R = np.zeros((n_points, 3, 3))
    R[..., -1] = d
    R[..., 0] = np.cross(d, np.random.randn(n_points, 3))
    R[..., 0] /= np.linalg.norm(R[..., 0], axis=-1)[..., None]
    R[..., 1] = np.cross(R[..., 2], R[..., 0])
    return R