# Tunnelvision

Tunnelvision is an experimental tensor viewer for IPython environments based on Voxel.

## Installation
Tunnelvision requires Python 3.7+. Binary wheels are available for MacOS (x86_64/arm64) and Linux.

To install Tunnelvision, run:

```bash
pip install tunnelvision
```

## Quick Start
The API of tunnelvision is very similar to that of [matplotlib](https://github.com/matplotlib/matplotlib). Tunnelvision is a 5D tensor viewer that requires tensors to have the following format: _Batch_ x _Depth_ x _Height_ x _Width_ x _Channels_, where channels can be 1 (grayscale/monochrome) or 3 (RGB). You can quickly plot (medical) images using:

```python
import numpy as np
import tunnelvision as tv

arr = np.random.randint(0, 2048, (2, 3, 224, 224, 1), dtype=np.uint16)
tv.show(arr)
```

More advanced plots with segmentation overlays (or colormaps in general) can be created as follows:
```python
ax = tv.Axes(figsize=(512, 512))
ax.imshow(arr1)
ax.imshow(arr2, cmap="seg")
ax.show()
```

[Pyvoxel](https://github.com/pyvoxel/pyvoxel) has support for tunnelvision as well, which allows you to plot images with their correct orientation and spacing, without having to manually set those in the configuration:

```python
import voxel as vx

mv = vx.load("../data/ct/")
tv.show(mv)
```

## VS Code Remote
To use tunnelvision through VS Code remote, we need forward an arbitrary available port to the tunnelvision-server. Once you have forwarded a port from the `ports` pane within VS Code, make sure to add it to your configuration file for tunnelvision:

```yaml
# ~/.cache/tunnelvision/default_config.yaml
port: 1337
```
