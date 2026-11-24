import glob
import math
import os
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import gaussian_filter
from shapely.geometry import LineString, box


def _read_asc_header(f):
  header = {}
  for _ in range(6):
    line = f.readline()
    if not line:
      raise ValueError("Incomplete .asc file header.")
    parts = line.strip().split()
    if len(parts) < 2:
      raise ValueError(f"Invalid .asc header line: {line!r}")
    raw_key, raw_val = parts[:2]
    key = raw_key.lower()
    val_str = raw_val.replace(",", ".")
    if key in ("ncols", "nrows"):
      header[key] = int(float(val_str))
    else:
      header[key] = float(val_str)
  return header


def _resolve_asc_list(dtm_path):
  if os.path.isdir(dtm_path):
    files = sorted(
        glob.glob(os.path.join(dtm_path, "*.asc"))
        + glob.glob(os.path.join(dtm_path, "*.ASC"))
    )
    return list(dict.fromkeys(files))
  if any(ch in dtm_path for ch in ("*", "?")):
    return sorted(glob.glob(dtm_path))
  if os.path.isfile(dtm_path):
    return [dtm_path]
  raise FileNotFoundError(f"DTM path not found: {dtm_path}")


def _inspect_asc_tile(asc_path):
  with open(asc_path, "r", encoding="utf-8", errors="ignore") as f:
    hdr = _read_asc_header(f)
  ncols = hdr["ncols"]
  nrows = hdr["nrows"]
  cs = hdr["cellsize"]
  nodata = hdr.get("nodata_value", -9999.0)
  x0 = hdr["xllcenter"] if "xllcenter" in hdr else hdr["xllcorner"] + 0.5 * cs
  y0 = hdr["yllcenter"] if "yllcenter" in hdr else hdr["yllcorner"] + 0.5 * cs
  y_top = y0 + (nrows - 1) * cs
  x_right = x0 + (ncols - 1) * cs
  return {
      "path": asc_path,
      "ncols": ncols,
      "nrows": nrows,
      "cs": cs,
      "nodata": nodata,
      "x0": x0,
      "y0": y0,
      "y_top": y_top,
      "x_right": x_right,
      "bbox": box(
          x0 - 0.5 * cs, y0 - 0.5 * cs, x_right + 0.5 * cs, y_top + 0.5 * cs
      ),
  }


def generate_contours_from_dtm(
    dtm_path,
    utm_bbox,
    step_m=25.0,
    major_step_m=100.0,
    smooth_sigma=1.0,
    min_length_m=35.0,
    utm_epsg="EPSG:32632",
):
  asc_files = _resolve_asc_list(dtm_path)
  if not asc_files:
    raise FileNotFoundError(f"No .asc files found in: {dtm_path}")

  xmin, ymin, xmax, ymax = utm_bbox.bounds
  pad_m = 150.0
  q_xmin = xmin - pad_m
  q_xmax = xmax + pad_m
  q_ymin = ymin - pad_m
  q_ymax = ymax + pad_m
  query_box = box(q_xmin, q_ymin, q_xmax, q_ymax)

  valid_tiles = []
  for fp in asc_files:
    try:
      info = _inspect_asc_tile(fp)
      if info["bbox"].intersects(query_box):
        valid_tiles.append(info)
    except Exception as exc:
      print(f"Warning: skipping unreadable DTM file '{fp}': {exc}", flush=True)

  if not valid_tiles:
    print(
        "Warning: map bounding box is outside the extent of provided DTM files.",
        flush=True,
    )
    return gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)

  if len(valid_tiles) > 1:
    names = ", ".join(os.path.basename(t["path"]) for t in valid_tiles)
    print(f"DTM mosaic from {len(valid_tiles)} tiles: {names}", flush=True)

  ref = next(iter(valid_tiles))
  cs = ref["cs"]
  c0_glob = int(math.floor((q_xmin - ref["x0"]) / cs))
  c1_glob = int(math.ceil((q_xmax - ref["x0"]) / cs))
  r0_glob = int(math.floor((ref["y_top"] - q_ymax) / cs))
  r1_glob = int(math.ceil((ref["y_top"] - q_ymin) / cs))

  xs = ref["x0"] + np.arange(c0_glob, c1_glob + 1, dtype=np.float64) * cs
  ys = ref["y_top"] - np.arange(r0_glob, r1_glob + 1, dtype=np.float64) * cs
  total_rows = ys.size
  total_cols = xs.size
  z_sub = np.full((total_rows, total_cols), np.nan, dtype=np.float64)

  for tile in valid_tiles:
    t_cs = tile["cs"]
    r_start = max(0, int(math.floor((tile["y_top"] - q_ymax) / t_cs)))
    r_end = min(
        tile["nrows"] - 1, int(math.ceil((tile["y_top"] - q_ymin) / t_cs))
    )
    c_start = max(0, int(math.floor((q_xmin - tile["x0"]) / t_cs)))
    c_end = min(
        tile["ncols"] - 1, int(math.ceil((q_xmax - tile["x0"]) / t_cs))
    )
    if r_start > r_end or c_start > c_end:
      continue

    with open(tile["path"], "r", encoding="utf-8", errors="ignore") as f:
      for _ in range(6 + r_start):
        if not f.readline():
          break

      for r_idx in range(r_start, r_end + 1):
        line = f.readline()
        if not line:
          break
        y_val = tile["y_top"] - r_idx * t_cs
        dst_r = int(round((ref["y_top"] - y_val) / cs)) - r0_glob
        if dst_r < 0 or dst_r >= total_rows:
          continue

        norm_line = line.replace(",", ".") if "," in line else line
        vals = np.fromstring(norm_line, sep=" ", dtype=np.float64)
        if vals.size < c_end + 1:
          continue

        row_slice = vals[c_start : c_end + 1]
        valid = ~np.isclose(row_slice, tile["nodata"])
        if not np.any(valid):
          continue

        x_vals = (
            tile["x0"] + np.arange(c_start, c_end + 1, dtype=np.float64) * t_cs
        )
        dst_cols = np.rint((x_vals - ref["x0"]) / cs).astype(int) - c0_glob
        in_bounds = (dst_cols >= 0) & (dst_cols < total_cols) & valid
        z_sub[dst_r, dst_cols[in_bounds]] = row_slice[in_bounds]

  if np.all(np.isnan(z_sub)):
    return gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)

  if smooth_sigma and smooth_sigma > 0:
    valid_mask = ~np.isnan(z_sub)
    z_zero = np.where(valid_mask, z_sub, 0.0)
    w_blur = gaussian_filter(valid_mask.astype(np.float64), sigma=smooth_sigma)
    z_blur = gaussian_filter(z_zero, sigma=smooth_sigma)
    with np.errstate(invalid="ignore", divide="ignore"):
      z_sub = np.where(w_blur > 0.1, z_blur / w_blur, np.nan)

  X, Y = np.meshgrid(xs, ys)
  z_min = float(np.nanmin(z_sub))
  z_max = float(np.nanmax(z_sub))
  lv_start = math.floor(z_min / step_m) * step_m
  lv_end = math.ceil(z_max / step_m) * step_m
  levels = np.arange(lv_start, lv_end + step_m * 0.5, step_m)
  levels = levels[(levels >= z_min) & (levels <= z_max)]

  if levels.size == 0:
    return gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)

  fig_tmp, ax_tmp = plt.subplots()
  try:
    cs_set = ax_tmp.contour(X, Y, z_sub, levels=levels)
    records = []
    for idx_lv, elev in enumerate(cs_set.levels):
      elev_int = int(round(float(elev)))
      is_major = (elev_int % int(round(major_step_m))) == 0
      ext_type = "elevation_major" if is_major else "elevation_minor"

      segs = cs_set.allsegs[idx_lv]
      for seg in segs:
        if len(seg) < 2:
          continue
        ls = LineString(seg)
        if ls.is_empty or ls.length < min_length_m:
          continue
        if not ls.intersects(utm_bbox):
          continue
        records.append({
            "contour": "elevation",
            "contour_ext": ext_type,
            "ele": str(elev_int),
            "elevation": str(elev_int),
            "name": str(elev_int),
            "clean_name": str(elev_int),
            "geometry": ls,
        })
  finally:
    plt.close(fig_tmp)

  if not records:
    return gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)

  return gpd.GeoDataFrame(records, crs=utm_epsg)
