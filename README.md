# blender-plots

Python API for plotting in blender 3.1.2

## Info

Blender can be a great tool for scientific visualization, but something as simple as making a plot with coordinates and
colors specified by numpy arrays still requires a lot of digging through the API.

The goal with this addon/library is to make the visualization process smoother by providing a matplotlib-like API for
making plots. It currently supports scatterplots through `bplt.Scatter`.

![out_15fps_v3_loop](https://user-images.githubusercontent.com/12471058/175826002-dc6ba8d5-a1c1-4b27-ae64-fc8085e46958.gif)


## Getting started

* Install the addon:
    * Option1: Go to `Code > Download ZIP` above and then in blender go to `Edit > Preferences > Add-ons > install` and
      select the downloaded file.
    * Option2: Git-clone this repo to the blender addons folder.
* Go to the addons panel in blender, search for `blender plots` and click on the tick-box.
* You should now be able to run `import blender_plots as bplt` in the python console.

Since the built-in text editor isn't great I recommend using [jupyterlab](https://jupyter.org/)
with
a [blender kernel](https://blender.stackexchange.com/questions/172249/how-can-i-use-blenders-python-api-from-a-ipython-terminal-or-jupyter-notebook)
for advanced use-cases.

## Examples

### Plotting functions

For now all the plotting is done through `bplt.Scatter` which expects an `Nx3` numpy array of xyz coordinates and
optionally an `Nx3` or `Nx4` numpy array with RGB or RGBA color values.

```
import numpy as np
import blender_plots as bplt
n, l = 150, 100
x, y = np.meshgrid(np.linspace(0, l, n), np.linspace(0, l, n))

z = np.sin(2*np.pi * x / l)*np.sin(2*np.pi * y / l) * 20
scatter = bplt.Scatter(np.stack([x, y, z], axis=-1).reshape(-1, 3), color=(1, 0, 0), name="red")

z = np.sin(4*np.pi * x / l)*np.sin(4*np.pi * y / l) * 20 + 40
scatter = bplt.Scatter(np.stack([x, y, z], axis=-1).reshape(-1, 3), color=(0, 0, 1), name="blue")
```

![image info](./images/sinusoids_editor.png)

### Animations
To get an animated plot, just pass in a `TxNx3` array of xyz coordinates instead:
```
# plot animated function
n, l, T = 150, 100, 100
t, x, y = np.meshgrid(np.arange(0, T), np.linspace(0, l, n), np.linspace(0, l, n), indexing='ij')

z = np.sin(2*np.pi * x / l) * np.sin(2*np.pi * y / l) * np.sin(2*np.pi * t / T) * 20
scatter = bplt.Scatter(np.stack([x, y, z], axis=-1).reshape(T, n*n, 3), color=(1, 0, 0), name="red")

z = np.sin(4*np.pi * x / l) * np.sin(4*np.pi * y / l) * np.sin(8*np.pi * t / T) * 20 + 40
scatter = bplt.Scatter(np.stack([x, y, z], axis=-1).reshape(T, n*n, 3), color=(0, 0, 1), name="blue")
```

https://user-images.githubusercontent.com/12471058/175825762-d208f9bf-7227-4e40-ba32-2871c7567206.mp4

### Visualizing point clouds

Since all heavy operations are done through numpy arrays or blender nodes it's possible to visualize large point clouds
with minimal overhead. For example, Here is one with 1M points:

```
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

```
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

```
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

### Custom mesh as marker

You can also use an existing mesh by passing it to `marker_type=...`:

```
bpy.ops.mesh.primitive_monkey_add()
monkey = bpy.context.active_object
monkey.hide_viewport = True
monkey.hide_render = True
n = int(.5e2)
scatter = bplt.Scatter(
    np.stack([
        np.cos(np.linspace(0, 1, n)*np.pi*4),
        np.sin(np.linspace(0, 1, n)*np.pi*4),
        np.linspace(0, 1, n)
    ], axis=-1) * 50,
    color=np.random.rand(n, 3),
    marker_type=monkey,
    radius_bottom=1,
    radius_top=3,
    marker_scale=[5]*3,
    randomize_rotation=True
)
```

![image info](./images/suzannes_spiral.png)

### Sphere markers

You can get perfect spheres as markers by passing in `marker_type="spheres"`. Though note that these are only visible in
the rendered view and with the rendering engine set to cycles

```
bplt.Scatter(
    np.random.rand(n, 3)*50,
    color=np.random.rand(n, 3),
    marker_type="spheres",
    radius=1.5
)
```

![image info](./images/spheres.png)
