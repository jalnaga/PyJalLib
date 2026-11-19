# PyJalLib

[한국어](https://github.com/jalnaga/PyJalLib/blob/master/README.ko.md) · [API reference](https://jalnaga.github.io/PyJalLib/) · [PyPI](https://pypi.org/project/pyjallib/)

PyJalLib is a Python library for building 3D game character pipelines. It helps
technical artists and pipeline developers rig characters in Autodesk 3ds Max,
import assets into Unreal Engine 5, and automate Perforce workflows.

## Features

- **3ds Max** — Build character rigs, edit skin weights, split morph targets, and automate FBX workflows with `pyjallib.max`.
- **Unreal Engine 5** — Import skeletal meshes and animations with Interchange or legacy import tools, and run headless imports with `pyjallib.ue5`.
- **Perforce** — Work with checkouts, changelists, and workspace sync through `pyjallib.perforce`.
- **Shared utilities** — Apply naming rules, derive asset paths, and scan `.max` files for candidate node and layer names without opening 3ds Max.

## Installation

PyJalLib requires Python 3.10 or later. Install the published release from PyPI.

```bash
python -m pip install pyjallib
```

Use the host application's Python environment for tools that work with a 3ds Max
scene (`pymxs`) or Unreal Editor assets (`unreal`). Morph splitting requires
NumPy 1.26 or later in the 3ds Max Python environment. The native Alpha Wrap
feature is unavailable in the PyPI distribution.

## Example

Split a morph pose into left and right targets. Run this in 3ds Max with a
neutral mesh named `Neutral` and a pose mesh named `Smile` that has matching
topology and vertex order.

```python
from pymxs import runtime as rt

from pyjallib.max import Morph

neutral_node = rt.getNodeByName("Neutral")
pose_node = rt.getNodeByName("Smile")
result = Morph().split_pose(neutral_node, pose_node, inAxis="X", inBandRatio=0.10)
left_node, right_node = result.leftNode, result.rightNode
```

The split uses object-space deltas and creates targets with `_L` and `_R`
suffixes while preserving the input meshes and selection. Use `inPlaneOffset`
to move the symmetry plane or `inBandHalfWidth` to override the ratio with an
explicit blend half-width. Invalid inputs and output name conflicts raise
`pyjallib.max.morphSplitService.SplitError`. Call `result.as_report()` to see the
effective blend half-width and maximum reconstruction error. For NumPy arrays
outside 3ds Max, use `pyjallib.max.morphMath.split_pose_deltas`.

## Contributing

For development setup and testing, see the
[contribution guide](https://github.com/jalnaga/PyJalLib/blob/master/CONTRIBUTING.md).
Report bugs or propose changes through [GitHub Issues](https://github.com/jalnaga/PyJalLib/issues).

## License

[MIT License](https://github.com/jalnaga/PyJalLib/blob/master/LICENSE).
