#!/usr/bin/env python3
"""Plot a field on a patch of an OpenFOAM case with a moving (deforming)
unstructured mesh, in 2D or in 3D, and save the figure as a PNG file.

The case can be reconstructed or decomposed (processor0, processor1... or
collated processors<N>). Only the functions readmesh, typefield and read* of
fluidfoam are used.

What is plotted:

* the norm of the field (default), or one of its components with
  --component: x, y, z for a vector; xx, xy, xz, yy, yz, zz for a symmetric
  tensor; xx, xy, xz, yx, yy, yz, zx, zy, zz for a tensor. The norm of a
  tensor is its Frobenius norm. A scalar field is plotted as it is.
* the field is given by --field (default: pointDisplacement). If it can not
  be used (it does not exist, or it is a point field such as
  pointDisplacement, not defined on the faces), the displacement of the face
  centres is plotted instead: centres at the chosen time minus centres at the
  initial time. The options --component and --scale apply to it.

Representation (--view):

* 2d: map of the patch projected on the plane given by --plane (xy, xz, yz);
* 3d: surface of the patch, coloured by the value, seen from the angle given
  by --elev and --azim (in degrees). The surface is triangulated in the
  plane given by --plane, so choose the plane in which the patch is a
  graph (for a bed: xy).

The positions of the faces are those of the chosen time (the deformed mesh).
--scale multiplies the displacement of the mesh (position at the chosen time
minus initial position) to make small deformations visible; it does not
change the values.

The value is known at the centre of the faces: it is interpolated between the
centres (2d), or constant on each triangle (3d).

The mesh must have been written in the time directories
(<time>/polyMesh/points) to see it deformed.

Usage:
    python plot_bed_displacement.py path_of_OpenFoam_case
    python plot_bed_displacement.py case --time 10 --patch bed --field D
    python plot_bed_displacement.py case --field D --component z
    python plot_bed_displacement.py case --field sigma --component xy
    python plot_bed_displacement.py case --view 3d --elev 40 --azim -120 --scale 5
"""

import argparse
import os
import re

import numpy as np
import matplotlib

matplotlib.use("Agg")  # no display needed (cluster, ssh...)
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 (registers the 3d projection)

from fluidfoam import (
    readmesh,
    readscalar,
    readsymmtensor,
    readtensor,
    readvector,
    typefield,
)

PLANES = {"xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}

READERS = {
    "scalar": readscalar,
    "vector": readvector,
    "symmtensor": readsymmtensor,
    "tensor": readtensor,
}

# index of each component in the arrays returned by fluidfoam (OpenFOAM order)
COMPONENTS = {
    "scalar": {},
    "vector": {"x": 0, "y": 1, "z": 2},
    "symmtensor": {"xx": 0, "xy": 1, "xz": 2, "yy": 3, "yz": 4, "zz": 5},
    "tensor": {
        "xx": 0, "xy": 1, "xz": 2,
        "yx": 3, "yy": 4, "yz": 5,
        "zx": 6, "zy": 7, "zz": 8,
    },
}  # fmt: skip

# the off-diagonal components of a symmetric tensor count twice in its norm
NORM_WEIGHTS = {"symmtensor": np.array([1, 2, 2, 1, 2, 1])}


def time_dirs(case):
    """Names of the time directories of the case, sorted by value.

    The first processor directory is also looked at, because the times are
    only there in a decomposed case.
    """
    directories = [case]
    for name in sorted(os.listdir(case)):
        if re.fullmatch(r"processors?\d+(_\d+-\d+)?", name):
            directories.append(os.path.join(case, name))
            break
    times = set()
    for directory in directories:
        for name in os.listdir(directory):
            try:
                float(name)
            except ValueError:
                continue
            if os.path.isdir(os.path.join(directory, name)):
                times.add(name)
    return sorted(times, key=float)


def patch_centres(case, patch, time=None):
    """Centres of the faces of the patch, array (3, n_faces).

    time=None: initial mesh (constant/polyMesh).
    """
    return np.array(
        readmesh(case, time_name=time, boundary=patch, verbose=False)
    )


def read_patch_field(case, time, field, patch, n_faces):
    """Field on the faces of the patch: type of the field and array
    (number of components, n_faces)."""
    kind = typefield(case, time, field, verbose=False)
    values = READERS[kind](case, time, field, boundary=patch, verbose=False)
    values = np.atleast_2d(values)
    if values.shape[1] == 1:  # uniform value on the patch
        values = np.repeat(values, n_faces, axis=1)
    if values.shape[1] != n_faces:
        raise ValueError(
            "%d values for %d faces: the field is not defined on the faces "
            "(point field?)" % (values.shape[1], n_faces)
        )
    return kind, values


def load_patch_data(case, time, patch, field):
    """Face centres of the patch (initial and at the given time) and field.

    Returns:
        initial: array (3, n_faces)
        centres: array (3, n_faces)
        kind: str, type of the field (scalar, vector, symmtensor, tensor)
        values: array (number of components, n_faces)
        source: str, name of what is plotted
    """
    try:
        initial = patch_centres(case, patch)
    except KeyError:
        raise SystemExit("Patch '%s' not found" % patch)
    except ValueError as error:  # decomposed case
        raise SystemExit("Patch '%s' not found (%s)" % (patch, error))
    try:
        centres = patch_centres(case, patch, time)
    except FileNotFoundError:
        print("No mesh written at time %s: the mesh is not moving" % time)
        centres = initial

    if field:
        try:
            kind, values = read_patch_field(
                case, time, field, patch, centres.shape[1]
            )
            return initial, centres, kind, values, field
        except (OSError, ValueError, KeyError, IndexError, SystemExit) as error:
            print("Field %s not used (%s)" % (field, error))
    print("Displacement computed from the motion of the face centres")
    return initial, centres, "vector", centres - initial, "displacement"


def select_component(values, kind, component):
    """Scalar value on each face: norm or component of the field."""
    if component == "norm":
        if kind == "scalar":
            return values[0]
        weights = NORM_WEIGHTS.get(kind, 1)
        return np.sqrt((weights * values.T**2).sum(axis=1))
    names = COMPONENTS[kind]
    if component not in names:
        available = ", ".join(["norm"] + list(names)) if names else "norm"
        raise SystemExit(
            "Component '%s' not available for a %s (available: %s)"
            % (component, kind, available)
        )
    return values[names[component]]


def make_label(source, kind, component):
    if kind == "scalar":
        return source
    if component == "norm":
        return "|%s|" % source
    return "%s_%s" % (source, component)


def color_settings(values, component, vmin, vmax, cmap):
    """Colormap and limits: symmetric limits and a diverging colormap if the
    values have both signs; from 0 for a norm."""
    signed = values.min() < 0
    if cmap is None:
        cmap = "RdBu_r" if signed else "viridis"
    if signed and vmin is None and vmax is None:
        vmax = np.abs(values).max()
        vmin = -vmax
    elif not signed and component == "norm" and vmin is None:
        vmin = 0
    return cmap, vmin, vmax


def make_triangulation(u, v, max_edge=None):
    triangulation = Triangulation(u, v)
    if max_edge is not None:  # remove the triangles bridging a hole
        corners = np.stack([u[triangulation.triangles], v[triangulation.triangles]])
        edges = np.linalg.norm(corners - np.roll(corners, 1, axis=2), axis=0)
        triangulation.set_mask(edges.max(axis=1) > max_edge)
    return triangulation


def plot_2d(positions, values, title, label, plane, output, limits, max_edge):
    cmap, vmin, vmax = limits
    u, v = positions[list(PLANES[plane])]
    triangulation = make_triangulation(u, v, max_edge)
    fig, ax = plt.subplots(figsize=(9, 6))
    image = ax.tripcolor(
        triangulation, values, shading="gouraud", cmap=cmap, vmin=vmin, vmax=vmax
    )
    ax.set_aspect("equal")
    ax.set_xlabel(plane[0])
    ax.set_ylabel(plane[1])
    ax.set_title(title)
    fig.colorbar(image, ax=ax).set_label(label)
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_3d(positions, values, title, label, plane, output, limits, max_edge, elev, azim):
    cmap, vmin, vmax = limits
    u, v = positions[list(PLANES[plane])]
    triangles = make_triangulation(u, v, max_edge).get_masked_triangles()
    x, y, z = positions
    fig = plt.figure(figsize=(10, 7))
    ax = fig.add_subplot(projection="3d")
    surface = ax.plot_trisurf(
        x, y, z, triangles=triangles, cmap=cmap, edgecolor="none"
    )
    # colour of a triangle: mean of the values of its three centres
    colours = values[triangles].mean(axis=1)
    surface.set_array(colours)
    # plot_trisurf scaled the colours on z: set the limits from the values
    surface.set_clim(
        colours.min() if vmin is None else vmin,
        colours.max() if vmax is None else vmax,
    )
    ax.view_init(elev=elev, azim=azim)
    extent = np.ptp(positions, axis=1)
    if hasattr(ax, "set_box_aspect"):  # same scale on the three axes
        ax.set_box_aspect(np.maximum(extent, 1e-9 * extent.max()))
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_zlabel("z")
    ax.set_title(title)
    fig.colorbar(surface, ax=ax, shrink=0.6, pad=0.1).set_label(label)
    fig.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("case", nargs="?", default=".", help="OpenFOAM case")
    parser.add_argument("--time", default="latestTime", help="time to plot")
    parser.add_argument("--patch", default="bed")
    parser.add_argument(
        "--field",
        default="pointDisplacement",
        help="field to plot (default: pointDisplacement); if it can not be "
        "used, the displacement of the face centres is plotted",
    )
    parser.add_argument(
        "--component",
        default="norm",
        help="norm (default) or a component: x, y, z (vector); xx, xy, xz, "
        "yy, yz, zz (symmetric tensor); xx, xy, xz, yx, yy, yz, zx, zy, zz "
        "(tensor)",
    )
    parser.add_argument("--view", default="2d", choices=("2d", "3d"))
    parser.add_argument("--elev", type=float, default=30.0, help="3d: elevation of the view (degrees)")
    parser.add_argument("--azim", type=float, default=-60.0, help="3d: azimuth of the view (degrees)")
    parser.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="factor applied to the displacement of the mesh (default: 1)",
    )
    parser.add_argument("--plane", default="xy", choices=sorted(PLANES))
    parser.add_argument("--output", default="bed_displacement.png")
    parser.add_argument("--vmin", type=float, default=None)
    parser.add_argument("--vmax", type=float, default=None)
    parser.add_argument("--cmap", default=None, help="matplotlib colormap")
    parser.add_argument(
        "--max-edge",
        type=float,
        default=None,
        help="remove the triangles with an edge longer than this length "
        "(holes, concave contours)",
    )
    args = parser.parse_args()

    time = args.time
    if time == "latestTime":
        time = time_dirs(args.case)[-1]

    initial, centres, kind, values, source = load_patch_data(
        args.case, time, args.patch, args.field
    )
    scalar = select_component(values, kind, args.component)
    label = make_label(source, kind, args.component)
    positions = initial + args.scale * (centres - initial)

    title = "%s on patch %s, t = %s" % (label, args.patch, time)
    if args.scale != 1:
        title += " (displacement x%g)" % args.scale
    limits = color_settings(scalar, args.component, args.vmin, args.vmax, args.cmap)
    if args.view == "2d":
        plot_2d(positions, scalar, title, label, args.plane, args.output, limits, args.max_edge)
    else:
        plot_3d(
            positions, scalar, title, label, args.plane, args.output, limits,
            args.max_edge, args.elev, args.azim,
        )  # fmt: skip
    print(
        "%d faces, %s from %.3g to %.3g -> %s"
        % (centres.shape[1], label, scalar.min(), scalar.max(), args.output)
    )


if __name__ == "__main__":
    main()
