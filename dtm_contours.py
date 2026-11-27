import glob
import math
import os
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from pyproj import CRS, Transformer
from scipy.ndimage import gaussian_filter
from shapely.geometry import LineString, box
from shapely.ops import transform as shp_transform


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
  return []


def _find_prj_crs(asc_path):
  base, _ = os.path.splitext(asc_path)
  for ext in (".prj", ".PRJ"):
    prj_path = base + ext
    if os.path.isfile(prj_path):
      try:
        with open(prj_path, "r", encoding="utf-8", errors="ignore") as f:
          wkt = f.read().strip()
        if wkt:
          return CRS.from_wkt(wkt), prj_path
      except Exception as exc:
        print(
            f"[WARNING] Unreadable .prj file '{prj_path}': {exc}",
            flush=True,
        )
  return None, None
def _check_empirical_utm_congruence(tile, utm_epsg):
  x_mid = 0.5 * (tile["x0"] + tile["x_right"])
  y_mid = 0.5 * (tile["y0"] + tile["y_top"])
  name = os.path.basename(tile["path"])

  if -180.0 <= x_mid <= 180.0 and -90.0 <= y_mid <= 90.0:
    return (
        f"[WARNING] DTM '{name}' has no .prj file and its coordinates "
        f"(X={x_mid:.4f}, Y={y_mid:.4f}) look like geographic degrees "
        f"(WGS84 / EPSG:4326) rather than projected {utm_epsg} meters."
    )

  if 1300000.0 <= x_mid <= 2800000.0 and 4000000.0 <= y_mid <= 5500000.0:
    return (
        f"[WARNING] DTM '{name}' has no .prj file and its coordinates "
        f"(X={int(x_mid)}, Y={int(y_mid)}) look like Italian Gauss-Boaga / "
        f"Monte Mario (EPSG:3003/3004) rather than {utm_epsg}."
    )

  if not (100000.0 <= x_mid <= 900000.0 and -10000000.0 <= y_mid <= 10000000.0):
    return (
        f"[WARNING] DTM '{name}' has no .prj file and its coordinates "
        f"(X={int(x_mid)}, Y={int(y_mid)}) fall outside standard UTM meter "
        f"bounds (possible feet units or local grid instead of {utm_epsg})."
    )

  return None


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
  crs_obj, prj_path = _find_prj_crs(asc_path)
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
      "crs": crs_obj,
      "prj_path": prj_path,
      "bbox": box(
          x0 - 0.5 * cs, y0 - 0.5 * cs, x_right + 0.5 * cs, y_top + 0.5 * cs
      ),
  }


def _crs_matches_target(src_crs, target_crs):
  if src_crs is None:
    return True
  if src_crs.equals(target_crs):
    return True
  src_epsg = src_crs.to_epsg()
  tgt_epsg = target_crs.to_epsg()
  if src_epsg and tgt_epsg and src_epsg == tgt_epsg:
    return True
  if src_epsg and tgt_epsg:
    if (32601 <= tgt_epsg <= 32660) and src_epsg == (25800 + (tgt_epsg - 32600)):
      return True
  return False
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
    print(
        f"[WARNING] No DTM (.asc) files found in '{dtm_path}'. "
        "Skipping contour line generation.",
        flush=True,
    )
    return gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)

  target_crs = CRS.from_user_input(utm_epsg)
  xmin, ymin, xmax, ymax = utm_bbox.bounds
  pad_m = 150.0
  query_box_utm = box(xmin - pad_m, ymin - pad_m, xmax + pad_m, ymax + pad_m)

  inspected = []
  warned_empirical = set()
  for fp in asc_files:
    try:
      info = _inspect_asc_tile(fp)
      if info["crs"] is None:
        emp_msg = _check_empirical_utm_congruence(info, utm_epsg)
        if emp_msg and emp_msg not in warned_empirical:
          print(emp_msg, flush=True)
          warned_empirical.add(emp_msg)
      inspected.append(info)
    except Exception as exc:
      print(f"[WARNING] Skipping unreadable DTM file '{fp}': {exc}", flush=True)

  if not inspected:
    print(
        f"[WARNING] No valid DTM (.asc) files could be read from '{dtm_path}'. "
        "Skipping contour line generation.",
        flush=True,
    )
    return gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)

  src_crs = next((t["crs"] for t in inspected if t["crs"] is not None), None)
  need_reproject = src_crs is not None and not _crs_matches_target(src_crs, target_crs)

  if need_reproject:
    to_src = Transformer.from_crs(target_crs, src_crs, always_xy=True).transform
    to_utm = Transformer.from_crs(src_crs, target_crs, always_xy=True).transform
    query_box_src = shp_transform(to_src, query_box_utm)
    src_label = src_crs.to_string() if src_crs.to_epsg() else src_crs.name
    print(
        f"DTM projection from .prj ({src_label}) differs from map ({utm_epsg}): "
        "reprojecting contours automatically...",
        flush=True,
    )
  else:
    to_utm = None
    query_box_src = query_box_utm

  valid_tiles = [t for t in inspected if t["bbox"].intersects(query_box_src)]

  if not valid_tiles:
    print(
        "[WARNING] Map bounding box is outside the extent of provided DTM files. "
        "Skipping contour line generation.",
        flush=True,
    )
    return gpd.GeoDataFrame(columns=["geometry"], crs=utm_epsg)

  if len(valid_tiles) > 1:
    names = ", ".join(os.path.basename(t["path"]) for t in valid_tiles)
    print(f"DTM mosaic from {len(valid_tiles)} tiles: {names}", flush=True)

  q_xmin, q_ymin, q_xmax, q_ymax = query_box_src.bounds
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

        row_slice = vals[slice(c_start, c_end + 1)]
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
        if need_reproject and to_utm is not None:
          ls = shp_transform(to_utm, ls)
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
