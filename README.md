# blender-plots

Python API for plotting in blender >=3.2

## Info

Blender can be a great tool for scientific visualization, but something as simple as making a plot with coordinates and
colors specified by numpy arrays still requires a lot of digging through the API.

The goal with this addon/library is to make the visualization process smoother by providing a matplotlib-like API for
making plots. It currently supports scatterplots through `bplt.Scatter`.


![out_15fps_v3_loop](https://user-images.githubusercontent.com/12471058/175826002-dc6ba8d5-a1c1-4b27-ae64-fc8085e46958.gif) ![image info](./images/arrows.png)


## Installation

### Option 1: Install with pip (recommended)

Run the following command in a terminal window:

```bash
[path_to_blender]/[version_number]/python/bin/python3.10 -m pip install blender_plots
```

This will download the library to `[path_to_blender]/[version_number]/python/lib/python3.10/site-packages/blender-plots`.

If you're using `blender_notebook` as described below you can instead pip install to the virtual environment to keep the Blender python environment clean. However with this method the library won't be available when lauching Blender without the notebook.

### Option 2: Install as addon

* Go to `Code > Download ZIP` above and then in blender go to `Edit > Preferences > Add-ons > install` and select the downloaded file (or simply git-clone this repo to the blender addons folder).
* Go to the addons panel in blender, search for `blender plots` and click on the tick-box.
* You should now be able to run `import blender_plots as bplt` in the python console.

### Set up blender notebook (optional)

Since the built-in code editor isn't great I recommend using jupyter notebooks with a [blender kernel](https://github.com/cheng-chi/blender_notebook) for script heavy use cases.

In a virtual environment, run:

```bash
python -m pip install pip install blender_notebook ipykernel
blender_notebook install --blender-exec [path_to_blender]/blender --kernel-name blender
```

You should then be able to select `blender` as kernel in your preferred notebook editor.

## Examples

### Scatterplots

Scatterplots can be created with `bplt.Scatter` which expects three arrays x, y, z with the same length `N`
containing coordinates to plot (or equivalently a single `Nx3` array as the first argument). Color can also be set using
the `color=` argument, which expects a`Nx3` or `Nx4` numpy array with RGB or RGBA color values. Passing in a single RGB
or RGBA value sets the same color for all points.

```python
import numpy as np
import blender_plots as bplt
n, l = 150, 100
x, y = np.meshgrid(np.linspace(0, l, n), np.linspace(0, l, n))
x, y = x.ravel(), y.ravel()

z = np.sin(2*np.pi * x / l)*np.sin(2*np.pi * y / l) * 20
bplt.Scatter(x, y, z, color=(1, 0, 0), name="red")

z = np.sin(4*np.pi * x / l)*np.sin(4*np.pi * y / l) * 20 + 40
bplt.Scatter(x, y, z, color=(0, 0, 1), name="blue")
```

![image info](./images/sinusoids_editor.png)

### Surface plots

Surface plots can be created in the same way, except using `MxNx3` arrays for x, y, z. Faces are then added between points neighbouring along the x and y axes. Colors and animation can be added in the same way as with scatterplots.

```python
import numpy as np
import blender_plots as bplt
n, l = 150, 100
x, y = np.meshgrid(np.linspace(0, l, n), np.linspace(0, l, n))

z = np.sin(2*np.pi * x / l)*np.sin(2*np.pi * y / l) * 20
bplt.Surface(x, y, z, color=(1, 0, 0), name="red")

z = np.sin(4*np.pi * x / l)*np.sin(4*np.pi * y / l) * 20 + 40
bplt.Surface(x, y, z, color=(0, 0, 1), name="blue")
```

![image info](./images/sinusoids_surface.png)

### Arrow plots

Create an arrow plot by providing an `Nx3` array of starting points and an `Nx3` array of vectors representing the arrows.

```python
import numpy as np
import blender_plots as bplt
import bpy

n, a, I = 25, 50, 100

bpy.ops.mesh.primitive_torus_add(major_radius=a, minor_radius=a / 100)
phis = np.linspace(0, 2 * np.pi, n)
thetas = np.linspace(0, 2 * np.pi, 1000)

def integrate_B(point):
    return I * a * (np.array([
        point[2] * np.cos(thetas),
        -point[2] * np.sin(thetas),
        -point[0] * np.cos(thetas) - point[1] * np.sin(thetas) + a
    ]) / np.linalg.norm(np.array([
        point[0] - a * np.cos(thetas),
        point[1] - a * np.sin(thetas),
        point[2] + np.zeros_like(thetas),
    ]), axis=0) ** 3).sum(axis=1) * (thetas[1] - thetas[0])

phis = np.linspace(0, 2 * np.pi, n)
thetas = np.linspace(0, 2 * np.pi, 100)

zeros = np.zeros(n)
for r in [a / 2, 3 * a / 4, a]:
    x, y, z = (a +  r * np.cos(phis)), zeros, r * np.sin(phis)
    points = np.array([x, y, z]).T
    B = np.apply_along_axis(integrate_B, 1, points)
    bplt.Arrows(points, B, color=(1, 0, 0), name=f"B_{r}", radius=.3, radius_ratio=3)

phis = np.linspace(0, 2 * np.pi, 13)
x, y, z = 1.01 * a * np.cos(phis), 1.01 * a * np.sin(phis), np.zeros(phis.shape)
points = np.array([x, y, z]).T
current_directions = np.array([-y, x, z]).T
bplt.Arrows(points, current_directions * .5, color=(0, 0, 1), name=f"I_directions", radius=.3, radius_ratio=3)
bplt.Scatter(points, color=(0, 0, 1), name=f"I_points", marker_type='ico_spheres', radius=1, subdivisions=3)
```

![image info](./images/arrows_editor.png)

### Animations

To get an animated plot, just pass in x, y, z as `TxN` arrays instead (or `TxNx3` as the first argument):

```python
import numpy as np
import blender_plots as bplt
n, l, T = 150, 100, 100
t, x, y = np.meshgrid(np.arange(0, T), np.linspace(0, l, n), np.linspace(0, l, n), indexing='ij')
t, x, y = t.reshape((T, -1)), x.reshape((T, -1)), y.reshape((T, -1))

z = np.sin(2*np.pi * x / l) * np.sin(2*np.pi * y / l) * np.sin(2*np.pi * t / T) * 20
bplt.Scatter(x, y, z, color=(1, 0, 0), name="red")

z = np.sin(4*np.pi * x / l) * np.sin(4*np.pi * y / l) * np.sin(8*np.pi * t / T) * 20 + 40
bplt.Scatter(x, y, z, color=(0, 0, 1), name="blue")
```

https://user-images.githubusercontent.com/12471058/175827154-f2788971-78d3-4778-937a-5d0ff30af7fd.mp4

For animated surface plots the input shape should be `TxMxNx3`.

### Visualizing point clouds

Since all heavy operations are done through numpy arrays or blender nodes it's possible to visualize large point clouds
with minimal overhead. For example, Here is one with 1M points:

```python
import numpy as np
import blender_plots as bplt
points = np.loadtxt("/home/linus/Downloads/tikal-guatemala-point-cloud/source/fovea_tikal_guatemala_pcloud.asc")
scatter = bplt.Scatter(points[:, :3] - points[0, :3], color=points[:, 3:]/255, size=(0.3,0.3,0.3))
```

![image info](./images/tikal.png)

You can find the
model [here](https://sketchfab.com/3d-models/tikal-guatemala-point-cloud-ea0a4612234c4aa3bad3ad68dd369953)
(select `.asc` format). Original source: [OpenHeritage](https://openheritage3d.org/project.php?id=708h-ss96),
license: [CC Attribution-NonCommercial-ShareAlikeCC](https://creativecommons.org/licenses/by-nc-sa/4.0/).

### Marker options

You can swap from the cube to any other mesh primitive using the `marker_type` argument. In blender 3.1 the options are
[cones](https://docs.blender.org/manual/en/3.1/modeling/geometry_nodes/mesh_primitives/cone.html),
[cubes](https://docs.blender.org/manual/en/3.1/modeling/geometry_nodes/mesh_primitives/cube.html),
[cylinders](https://docs.blender.org/manual/en/3.1/modeling/geometry_nodes/mesh_primitives/cylinder.html),
[grids](https://docs.blender.org/manual/en/3.1/modeling/geometry_nodes/mesh_primitives/grid.html),
[ico_spheres](https://docs.blender.org/manual/en/3.1/modeling/geometry_nodes/mesh_primitives/icosphere.html),
[circles](https://docs.blender.org/manual/en/3.1/modeling/geometry_nodes/mesh_primitives/mesh_circle.html),
[lines](https://docs.blender.org/manual/en/3.1/modeling/geometry_nodes/mesh_primitives/mesh_line.html) or
[uv_spheres](https://docs.blender.org/manual/en/3.1/modeling/geometry_nodes/mesh_primitives/uv_sphere.html).

![image info](./images/markers.png)

Each marker type can further be configured by passing in node settings as parameter arguments. For example from
the [cone node](https://docs.blender.org/manual/en/3.1/modeling/geometry_nodes/mesh_primitives/cone.html)
docs we can see that it has the parameters `Radius Top` and `Radius Bottom`, these can be set directly by
passing `radius_top=...`
and `radius_bottom=...` to `bplt.Scatter`:

```python
import numpy as np
import blender_plots as bplt
n = int(1e2)
scatter = bplt.Scatter(
    np.random.rand(n, 3)*50,
    color=np.random.rand(n, 3),
    marker_type="cones",
    radius_bottom=1,
    radius_top=3,
    randomize_rotation=True
)
```

![image info](./images/cones.png)

Similarly, the [cube node](https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/mesh_primitives/cube.html)
has a vector-valued `Size` parameter:

```python
import numpy as np
import blender_plots as bplt
n = int(1e2)
bplt.Scatter(
    np.random.rand(n, 3)*50,
    color=np.random.rand(n, 3),
    size=(5, 1, 1),
    randomize_rotation=True
)
```

![image info](./images/rotated.png)

This is achieved by automatically converting input arguments to geometry node properties.
See [blender_utils.py](https://github.com/Linusnie/blender_plots/blob/main/blender_utils.py)
for more details.

### Rotating markers
Each marker can be assigned a rotation using the argument `marker_rotation=...`, similarly to the color argument it
supports passing a single value for all points, one for each point, or one for each point and timestamp.
The supported formats are XYZ euler angles in radians (by passing an Nx3 or NxTx3 array) or rotation matrices
(by passing a Nx3x3 or NxTx3x3 array). As shown in the previous examples passing `randomize_rotation=True` assigns a
random rotation to each marker.

```python
import numpy as np
import blender_plots as bplt
def get_rotaitons_facing_point(origin, points):
    n_points = len(points)
    d = (origin - points) / np.linalg.norm(origin - points, axis=-1)[:, None]
    R = np.zeros((n_points, 3, 3))
    R[..., -1] = d
    R[..., 0] = np.cross(d, np.random.randn(n_points, 3))
    R[..., 0] /= np.linalg.norm(R[..., 0], axis=-1)[..., None]
    R[..., 1] = np.cross(R[..., 2], R[..., 0])
    return R

n = 5000
points = np.random.randn(n, 3) * 20
rots = get_rotaitons_facing_point(np.zeros(3), points)
s = bplt.Scatter(
    points,
    marker_rotation=rots,
    color=np.array([[1.0, 0.1094, 0.0], [0.0, 0.1301, 1.0]])[np.random.randint(2, size=n)],
    size=(1, 1, 5),
)
```

![image info](./images/rots.png)

### Custom mesh as marker

You can also use an existing mesh by passing it to `marker_type=...`:

```python
import numpy as np
from colorsys import hls_to_rgb
import bpy
import blender_plots as bplt
bpy.ops.mesh.primitive_monkey_add()
monkey = bpy.context.active_object
monkey.hide_viewport = True
monkey.hide_render = True
n = int(.5e2)

scatter = bplt.Scatter(
    50 * np.cos(np.linspace(0, 1, n)*np.pi*4),
    50 * np.sin(np.linspace(0, 1, n)*np.pi*4),
    50 * np.linspace(0, 1, n),
    color=np.array([hls_to_rgb(2/3 * i/(n-1), 0.5, 1) for i in range(n)]),
    marker_type=monkey,
    radius_bottom=1,
    radius_top=3,
    marker_scale=[5]*3,
    marker_rotation=np.array([np.zeros(n), np.zeros(n), np.pi/2 + np.linspace(0, 4 * np.pi, n)]).T,
)
```

![image info](./images/suzannes_spiral.png)

### Sphere markers

You can get perfect spheres as markers by passing in `marker_type="spheres"`. Though note that these are only visible in
the rendered view and with the rendering engine set to cycles

```python
import numpy as np
import blender_plots as bplt
n = int(1e2)
bplt.Scatter(
    np.random.rand(n, 3)*50,
    color=np.random.rand(n, 3),
    marker_type="spheres",
    radius=1.5
)
```

![image info](./images/spheres.png)
