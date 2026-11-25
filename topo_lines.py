import math
import geopandas as gpd
import matplotlib.patheffects as path_effects
import pandas as pd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge


def _col(df, name):
  return df[name] if name in df.columns else pd.Series(None, index=df.index)


CRT_ROAD_STYLES = [
    (
        "footpaths",
        lambda df: _col(df, "highway").isin(
            ["path", "footway", "steps", "bridleway", "via_ferrata"]
        ),
        "none",
        0,
        "#000000",
        0.55,
        (0, (2.5, 2.5)),
        1.0,
        35,
    ),
    (
        "cycleways",
        lambda df: _col(df, "highway") == "cycleway",
        "none",
        0,
        "#0054ff",
        0.85,
        (0, (2.5, 2.1)),
        1.0,
        36,
    ),
    (
        "service_roads",
        lambda df: _col(df, "highway") == "service",
        "#000000",
        1.0,
        "#ffffff",
        0.65,
        "-",
        1.0,
        39.5,
    ),
    (
        "minor_roads",
        lambda df: _col(df, "highway").isin([
            "unclassified",
            "residential",
            "living_street",
            "pedestrian",
        ]),
        "#000000",
        1.45,
        "#ffffff",
        1.0,
        "-",
        1.0,
        40,
    ),
    (
        "tertiary_roads",
        lambda df: _col(df, "highway").isin(["tertiary", "tertiary_link"]),
        "#000000",
        2.0,
        "#ffffff",
        1.4,
        "-",
        1.0,
        42,
    ),
    (
        "secondary_roads",
        lambda df: _col(df, "highway").isin(["secondary", "secondary_link"]),
        "#000000",
        2.3,
        "#fff65c",
        1.7,
        "-",
        1.0,
        44,
    ),
    (
        "primary_roads",
        lambda df: _col(df, "highway").isin(["primary", "primary_link"]),
        "#000000",
        2.5,
        "#fff65c",
        1.9,
        "-",
        1.0,
        46,
    ),
    (
        "trunk_roads",
        lambda df: _col(df, "highway").isin(["trunk", "trunk_link"]),
        "#000000",
        2.8,
        "#f7bc86",
        2.1,
        "-",
        1.0,
        48,
    ),
    (
        "motorways",
        lambda df: _col(df, "highway").isin(["motorway", "motorway_link"]),
        "#000000",
        3.1,
        "#e890a0",
        2.3,
        "-",
        1.0,
        50,
    ),
]


def _generate_parallels(gdf, distance_m):
  geoms_left = []
  geoms_right = []
  for geom in gdf.geometry:
    if geom is None or geom.is_empty:
      continue
    g_left = geom.parallel_offset(distance_m, "left", join_style=2)
    g_right = geom.parallel_offset(distance_m, "right", join_style=2)
    if not g_left.is_empty:
      geoms_left.append(g_left)
    if not g_right.is_empty:
      geoms_right.append(g_right)
  gs_left = (
      gpd.GeoSeries(geoms_left, crs=gdf.crs)
      if geoms_left
      else gpd.GeoSeries([], crs=gdf.crs)
  )
  gs_right = (
      gpd.GeoSeries(geoms_right, crs=gdf.crs)
      if geoms_right
      else gpd.GeoSeries([], crs=gdf.crs)
  )
  return gs_left, gs_right


def _draw_topo_tracks(ax, lines, is_tunnel, scale=25000, symscale=1.0):
  # Half-offset of 0.20 mm on paper -> total track width 0.40 mm (as in TOPO)
  offset_m = (0.20 * symscale * float(scale)) / 1000.0
  is_track = _col(lines, "highway") == "track"
  is_rough = is_track & _col(lines, "tracktype").isin(["grade4", "grade5"])
  is_norm = is_track & (~_col(lines, "tracktype").isin(["grade4", "grade5"]))

  rough_surf = lines[is_rough & (~is_tunnel)]
  rough_tunn = lines[is_rough & is_tunnel]
  if not rough_surf.empty:
    rough_surf.plot(
        ax=ax, color="#ffffff", linewidth=0.65 * symscale, zorder=37.0
    )
    gs_left, gs_right = _generate_parallels(rough_surf, offset_m)
    if not gs_left.empty:
      gs_left.plot(
          ax=ax,
          color="#000000",
          linewidth=0.40 * symscale,
          linestyle=(0, (2.6, 1.8)),
          zorder=37.1,
      )
    if not gs_right.empty:
      gs_right.plot(
          ax=ax,
          color="#000000",
          linewidth=0.40 * symscale,
          linestyle=(0, (2.6, 1.8)),
          zorder=37.1,
      )
  if not rough_tunn.empty:
    rough_tunn.plot(
        ax=ax,
        color="#666666",
        linewidth=0.85 * symscale,
        linestyle="--",
        alpha=0.75,
        zorder=37.0,
    )

  norm_surf = lines[is_norm & (~is_tunnel)]
  norm_tunn = lines[is_norm & is_tunnel]
  if not norm_surf.empty:
    norm_surf.plot(
        ax=ax, color="#ffffff", linewidth=0.65 * symscale, zorder=38.0
    )
    gs_left, gs_right = _generate_parallels(norm_surf, offset_m)
    if not gs_left.empty:
      gs_left.plot(
          ax=ax,
          color="#000000",
          linewidth=0.40 * symscale,
          linestyle="-",
          zorder=38.1,
      )
    if not gs_right.empty:
      gs_right.plot(
          ax=ax,
          color="#000000",
          linewidth=0.40 * symscale,
          linestyle=(0, (2.8, 1.8)),
          zorder=38.1,
      )
  if not norm_tunn.empty:
    norm_tunn.plot(
        ax=ax,
        color="#666666",
        linewidth=0.95 * symscale,
        linestyle="--",
        alpha=0.75,
        zorder=38.0,
    )


def _detect_major_contours(df, major_step_m=100.0):
  if "contour_ext" in df.columns:
    has_ext = df["contour_ext"].isin(["elevation_major", "elevation_minor"])
    if has_ext.any():
      return df["contour_ext"] == "elevation_major"
  is_main = pd.Series(False, index=df.index)
  step = max(1, int(round(float(major_step_m))))
  for col in ("ele", "elevation"):
    if col in df.columns:
      elevs = pd.to_numeric(df[col], errors="coerce")
      is_main = is_main | (elevs.notna() & ((elevs.round() % step) == 0))
  return is_main


def _extract_elevation_text(row):
  for col in ("ele", "elevation", "name"):
    val = row.get(col)
    if val is not None and pd.notna(val):
      num = pd.to_numeric(val, errors="coerce")
      if pd.notna(num):
        return f"{int(round(float(num)))}"
  return ""


def _label_major_contours(ax, c_pri, utm_bbox):
  xmin, ymin, xmax, ymax = utm_bbox.bounds
  margin = 180.0
  placed_points = []
  min_dist_sq = 450.0 * 450.0
  repeat_step = 1400.0

  for _, row in c_pri.iterrows():
    text = _extract_elevation_text(row)
    if not text:
      continue
    geom = row.geometry
    if geom is None or geom.is_empty:
      continue

    parts = (
        list(geom.geoms)
        if isinstance(geom, MultiLineString)
        else ([geom] if isinstance(geom, LineString) else [])
    )

    for ls in parts:
      length = ls.length
      if length < 260.0:
        continue

      n_lbl = max(1, int(length // repeat_step))
      for k in range(n_lbl):
        dist = length * (k + 0.5) / n_lbl
        pt = ls.interpolate(dist)
        px, py = pt.x, pt.y

        if (
            px < xmin + margin
            or px > xmax - margin
            or py < ymin + margin
            or py > ymax - margin
        ):
          continue

        if any(
            (px - ox) ** 2 + (py - oy) ** 2 < min_dist_sq
            for ox, oy in placed_points
        ):
          continue

        p_prev = ls.interpolate(max(0.0, dist - 20.0))
        p_next = ls.interpolate(min(length, dist + 20.0))
        dx = p_next.x - p_prev.x
        dy = p_next.y - p_prev.y
        if dx == 0.0 and dy == 0.0:
          ang = 0.0
        else:
          ang = math.degrees(math.atan2(dy, dx))
          if ang > 90.0:
            ang -= 180.0
          elif ang < -90.0:
            ang += 180.0

        txt = ax.text(
            px,
            py,
            text,
            fontsize=4.6,
            fontweight="bold",
            color="#7a3500",
            ha="center",
            va="center",
            rotation=ang,
            rotation_mode="anchor",
            zorder=17,
        )
        txt.set_path_effects([
            path_effects.Stroke(linewidth=1.4, foreground="#ffffff", alpha=0.82),
            path_effects.Normal(),
        ])
        placed_points.append((px, py))


def draw_lines_and_contours(
    ax,
    lines,
    gdf_contours,
    utm_bbox,
    scale=25000,
    major_step_m=100.0,
    symscale=1.0,
):
  if gdf_contours is not None and not gdf_contours.empty:
    c_clip = gpd.clip(gdf_contours, utm_bbox)
    if not c_clip.empty:
      has_contour_tag = (
          (_col(c_clip, "contour") == "elevation")
          | _col(c_clip, "contour_ext").isin(["elevation_major", "elevation_minor"])
      )
      c_clip = c_clip[has_contour_tag]
    if not c_clip.empty:
      is_main = _detect_major_contours(c_clip, major_step_m=major_step_m)
      c_sec = c_clip[~is_main]
      c_pri = c_clip[is_main]
      if not c_sec.empty:
        c_sec.plot(
            ax=ax, color="#d98a2b", linewidth=0.25, alpha=0.55, zorder=15
        )
      if not c_pri.empty:
        c_pri.plot(
            ax=ax, color="#c85a00", linewidth=0.60, alpha=0.80, zorder=16
        )
        _label_major_contours(ax, c_pri, utm_bbox)

  if lines.empty:
    return

  rivers = lines[_col(lines, "waterway").isin(["river", "canal"])]
  if not rivers.empty:
    rivers.plot(ax=ax, color="#247ba0", linewidth=2.2 * symscale, zorder=18.1)
    rivers.plot(ax=ax, color="#72d6ff", linewidth=1.6 * symscale, zorder=18.2)

  streams = lines[_col(lines, "waterway") == "stream"]
  if not streams.empty:
    streams.plot(ax=ax, color="#5cc2d1", linewidth=0.85 * symscale, zorder=18.05)

  ditches = lines[_col(lines, "waterway").isin(["drain", "ditch"])]
  if not ditches.empty:
    ditches.plot(
        ax=ax,
        color="#5cc2d1",
        linewidth=0.45 * symscale,
        linestyle=(0, (3, 1.5)),
        zorder=18.0,
    )

  runways = lines[_col(lines, "aeroway") == "runway"]
  if not runways.empty:
    runways.plot(ax=ax, color="#555555", linewidth=3.5 * symscale, zorder=39)

  route_h = lines[_col(lines, "route") == "hiking"]
  if not route_h.empty:
    merged_h = linemerge(route_h.geometry.unary_union)
    gpd.GeoSeries([merged_h], crs=route_h.crs).plot(
        ax=ax,
        color="#e60000",
        linewidth=2.2 * symscale,
        alpha=0.38,
        capstyle="butt",
        joinstyle="round",
        zorder=51,
    )

  route_b = lines[_col(lines, "route").isin(["bicycle", "mtb"])]
  if not route_b.empty:
    merged_b = linemerge(route_b.geometry.unary_union)
    gpd.GeoSeries([merged_b], crs=route_b.crs).plot(
        ax=ax,
        color="#8e007a",
        linewidth=2.2 * symscale,
        alpha=0.38,
        capstyle="butt",
        joinstyle="round",
        zorder=51.1,
    )

  is_tunnel = _col(lines, "tunnel").isin(["yes", "building_passage"])
  _draw_topo_tracks(ax, lines, is_tunnel, scale=scale, symscale=symscale)

  for (
      _,
      filter_fn,
      col_b,
      lw_b,
      col_f,
      lw_f,
      ls,
      alpha,
      zord,
  ) in CRT_ROAD_STYLES:
    mask = filter_fn(lines)
    norm = lines[mask & (~is_tunnel)]
    tunn = lines[mask & is_tunnel]

    if not norm.empty:
      if col_b != "none":
        norm_u = gpd.GeoSeries([norm.geometry.unary_union], crs=norm.crs)
        norm_u.plot(
            ax=ax,
            color=col_b,
            linewidth=lw_b * symscale,
            capstyle="round",
            joinstyle="round",
            zorder=zord,
        )
        norm_u.plot(
            ax=ax,
            color=col_f,
            linewidth=lw_f * symscale,
            linestyle=ls,
            alpha=alpha,
            capstyle="round",
            joinstyle="round",
            zorder=zord + 0.1,
        )
      else:
        norm.plot(
            ax=ax,
            color=col_f,
            linewidth=lw_f * symscale,
            linestyle=ls,
            alpha=alpha,
            zorder=zord + 0.1,
        )
    if not tunn.empty:
      tunn.plot(
          ax=ax,
          color="#666666",
          linewidth=max(lw_f, 1.0) * symscale,
          linestyle="--",
          alpha=0.75,
          zorder=zord,
      )

  railways = lines[
      _col(lines, "railway").isin(["rail", "narrow_gauge", "light_rail"])
  ]
  if not railways.empty:
    rail_tunnel = _col(railways, "tunnel").isin(["yes", "building_passage"])
    rail_norm = railways[~rail_tunnel]
    rail_tunn = railways[rail_tunnel]

    if not rail_norm.empty:
      rail_norm.plot(
          ax=ax,
          color="#000000",
          linewidth=1.45 * symscale,
          capstyle="butt",
          zorder=52,
      )
      rail_norm.plot(
          ax=ax,
          color="#ffffff",
          linewidth=0.90 * symscale,
          linestyle=(0, (3.2, 3.2)),
          capstyle="butt",
          zorder=52.1,
      )

    if not rail_tunn.empty:
      rail_tunn.plot(
          ax=ax,
          color="#666666",
          linewidth=1.35 * symscale,
          linestyle="--",
          alpha=0.75,
          zorder=52,
      )
      rail_tunn.plot(
          ax=ax,
          color="#ffffff",
          linewidth=0.80 * symscale,
          linestyle=(0, (3.2, 3.2)),
          alpha=0.85,
          zorder=52.1,
      )

  aerialways = lines[
      (_col(lines, "aerialway").notna() & (_col(lines, "aerialway") != "no"))
      | (_col(lines, "railway") == "funicular")
  ]
  if not aerialways.empty:
    aerialways.plot(ax=ax, color="#000000", linewidth=0.65 * symscale, zorder=53)
    aerialways.plot(
        ax=ax,
        color="#000000",
        linewidth=2.3 * symscale,
        linestyle=(0, (0.7, 5.5)),
        zorder=53.1,
    )

  dams_l = lines[
      _col(lines, "waterway").isin(["dam", "weir"])
      | (_col(lines, "man_made").isin(["dam", "weir"]))
  ]
  if not dams_l.empty:
    dams_l.plot(
        ax=ax,
        color="#000000",
        linewidth=1.1 * symscale,
        capstyle="butt",
        zorder=34,
    )
    offset_dam_m = (0.35 * symscale * float(scale)) / 1000.0
    _, gs_downstream = _generate_parallels(dams_l, offset_dam_m)
    if not gs_downstream.empty:
      gs_downstream.plot(
          ax=ax,
          color="#000000",
          linewidth=1.5 * symscale,
          linestyle=(0, (1.2, 2.4)),
          capstyle="butt",
          zorder=34.1,
      )
