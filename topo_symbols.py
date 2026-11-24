import matplotlib.path as mpath
import numpy as np


def _create_church_marker():
  verts = [
      (-0.5, -0.8),
      (0.5, -0.8),
      (0.5, 0.0),
      (-0.5, 0.0),
      (-0.5, -0.8),
      (0.0, 0.0),
      (0.0, 0.9),
      (-0.4, 0.55),
      (0.4, 0.55),
  ]
  codes = [
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.CLOSEPOLY,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
  ]
  return mpath.Path(verts, codes)


def _create_alpine_hut_marker():
  verts = [
      (-0.7, -0.7),
      (0.7, -0.7),
      (0.7, 0.1),
      (0.0, 0.8),
      (-0.7, 0.1),
      (-0.7, -0.7),
  ]
  codes = [
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.CLOSEPOLY,
  ]
  return mpath.Path(verts, codes)


def _create_wayside_cross_marker():
  verts = [
      (0.0, -0.85),
      (0.0, 0.85),
      (-0.55, 0.35),
      (0.55, 0.35),
  ]
  codes = [
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
  ]
  return mpath.Path(verts, codes)


def _create_cave_marker():
  angles = np.linspace(0, np.pi, 20)
  verts = [(0.75 * np.cos(a), 0.75 * np.sin(a) - 0.3) for a in angles]
  codes = [mpath.Path.MOVETO] + [mpath.Path.LINETO] * (len(verts) - 1)
  return mpath.Path(verts, codes)


def _create_viewpoint_marker():
  verts = []
  codes = []
  for ang in np.linspace(0, 2 * np.pi, 6, endpoint=False):
    verts.extend([
        (0.35 * np.cos(ang), 0.35 * np.sin(ang)),
        (0.95 * np.cos(ang), 0.95 * np.sin(ang)),
    ])
    codes.extend([mpath.Path.MOVETO, mpath.Path.LINETO])
  return mpath.Path(verts, codes)


def _create_drop_marker():
  angles = np.linspace(-np.pi, 0, 16)
  arc = [(0.55 * np.cos(a), 0.55 * np.sin(a) - 0.25) for a in angles]
  verts = [(0.0, 0.85)] + arc + [(0.0, 0.85)]
  codes = (
      [mpath.Path.MOVETO]
      + [mpath.Path.LINETO] * len(arc)
      + [mpath.Path.CLOSEPOLY]
  )
  return mpath.Path(verts, codes)


def _create_saddle_marker():
  t = np.linspace(-1, 1, 12)
  left = [(-0.25 - 0.45 * (y**2), y * 0.8) for y in t]
  right = [(0.25 + 0.45 * (y**2), y * 0.8) for y in t]
  verts = left + right
  codes = (
      [mpath.Path.MOVETO]
      + [mpath.Path.LINETO] * (len(left) - 1)
      + [mpath.Path.MOVETO]
      + [mpath.Path.LINETO] * (len(right) - 1)
  )
  return mpath.Path(verts, codes)


def _create_ford_marker():
  x = np.linspace(-0.8, 0.8, 16)
  wave1 = [(xi, 0.25 * np.sin(xi * 4.0) + 0.25) for xi in x]
  wave2 = [(xi, 0.25 * np.sin(xi * 4.0) - 0.25) for xi in x]
  verts = wave1 + wave2
  codes = (
      [mpath.Path.MOVETO]
      + [mpath.Path.LINETO] * (len(wave1) - 1)
      + [mpath.Path.MOVETO]
      + [mpath.Path.LINETO] * (len(wave2) - 1)
  )
  return mpath.Path(verts, codes)


def _create_quarry_marker():
  verts = [
      (-0.6, -0.6),
      (0.6, 0.6),
      (0.6, -0.6),
      (-0.6, 0.6),
      (-0.7, 0.35),
      (-0.35, 0.7),
      (0.35, 0.7),
      (0.7, 0.35),
  ]
  codes = [
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
  ]
  return mpath.Path(verts, codes)


def _create_landfill_marker():
  verts = [
      (-0.55, 0.45),
      (0.55, 0.45),
      (0.4, -0.75),
      (-0.4, -0.75),
      (-0.55, 0.45),
      (-0.7, 0.6),
      (0.7, 0.6),
      (-0.25, 0.6),
      (-0.25, 0.85),
      (0.25, 0.85),
      (0.25, 0.6),
  ]
  codes = [
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.CLOSEPOLY,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
  ]
  return mpath.Path(verts, codes)


def _create_train_marker():
  verts = [
      (-0.5, -0.45),
      (0.5, -0.45),
      (0.5, 0.65),
      (-0.5, 0.65),
      (-0.5, -0.45),
      (-0.35, 0.1),
      (0.35, 0.1),
      (0.35, 0.48),
      (-0.35, 0.48),
      (-0.35, 0.1),
      (-0.65, -0.8),
      (-0.25, -0.45),
      (0.65, -0.8),
      (0.25, -0.45),
  ]
  codes = [
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.CLOSEPOLY,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.CLOSEPOLY,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
  ]
  return mpath.Path(verts, codes)


def _create_tent_marker():
  verts = [
      (-0.8, -0.65),
      (0.0, 0.75),
      (0.8, -0.65),
      (-0.8, -0.65),
      (-0.25, -0.65),
      (0.0, 0.05),
      (0.25, -0.65),
  ]
  codes = [
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.CLOSEPOLY,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
  ]
  return mpath.Path(verts, codes)


def _create_golf_marker():
  verts = [
      (-0.35, -0.75),
      (-0.35, 0.85),
      (0.65, 0.45),
      (-0.35, 0.1),
      (-0.65, -0.75),
      (0.0, -0.75),
  ]
  codes = [
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
  ]
  return mpath.Path(verts, codes)


def _create_antenna_marker():
  # Communication tower / lattice mast with radio waves
  verts = [
      (-0.45, -0.8),
      (0.0, 0.75),
      (0.45, -0.8),
      (-0.25, -0.15),
      (0.25, -0.15),
      (-0.55, 0.55),
      (-0.35, 0.85),
      (0.55, 0.55),
      (0.35, 0.85),
  ]
  codes = [
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
  ]
  return mpath.Path(verts, codes)


def _create_gate_marker():
  # Road barrier / gate
  verts = [
      (-0.75, 0.0),
      (0.75, 0.0),
      (-0.75, -0.35),
      (-0.75, 0.35),
      (0.75, -0.35),
      (0.75, 0.35),
  ]
  codes = [
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
      mpath.Path.MOVETO,
      mpath.Path.LINETO,
  ]
  return mpath.Path(verts, codes)


def _create_castle_marker():
  # Battlemented tower / castle with 3 merlons
  verts = [
      (-0.65, -0.85),
      (0.65, -0.85),
      (0.58, 0.35),
      (0.72, 0.35),
      (0.72, 0.90),
      (0.36, 0.90),
      (0.36, 0.42),
      (0.18, 0.42),
      (0.18, 0.90),
      (-0.18, 0.90),
      (-0.18, 0.42),
      (-0.36, 0.42),
      (-0.36, 0.90),
      (-0.72, 0.90),
      (-0.72, 0.35),
      (-0.58, 0.35),
      (-0.65, -0.85),
  ]
  codes = (
      [mpath.Path.MOVETO]
      + [mpath.Path.LINETO] * (len(verts) - 2)
      + [mpath.Path.CLOSEPOLY]
  )
  return mpath.Path(verts, codes)


def _create_airplane_marker():
  verts = [
      (0.0, 0.90),
      (0.20, 0.45),
      (0.92, 0.10),
      (0.92, -0.18),
      (0.20, 0.02),
      (0.18, -0.45),
      (0.50, -0.72),
      (0.50, -0.90),
      (0.0, -0.72),
      (-0.50, -0.90),
      (-0.50, -0.72),
      (-0.18, -0.45),
      (-0.20, 0.02),
      (-0.92, -0.18),
      (-0.92, 0.10),
      (-0.20, 0.45),
      (0.0, 0.90),
  ]
  codes = (
      [mpath.Path.MOVETO]
      + [mpath.Path.LINETO] * (len(verts) - 2)
      + [mpath.Path.CLOSEPOLY]
  )
  return mpath.Path(verts, codes)


TOPO_MARKERS = {
    "church": _create_church_marker(),
    "alpine_hut": _create_alpine_hut_marker(),
    "wayside_cross": _create_wayside_cross_marker(),
    "cave": _create_cave_marker(),
    "viewpoint": _create_viewpoint_marker(),
    "drop": _create_drop_marker(),
    "saddle": _create_saddle_marker(),
    "ford": _create_ford_marker(),
    "quarry": _create_quarry_marker(),
    "landfill": _create_landfill_marker(),
    "train": _create_train_marker(),
    "tent": _create_tent_marker(),
    "golf": _create_golf_marker(),
    "antenna": _create_antenna_marker(),
    "gate": _create_gate_marker(),
    "castle": _create_castle_marker(),
    "airplane": _create_airplane_marker(),
}
