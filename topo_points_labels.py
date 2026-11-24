import math
from topo_classifier import classify_feature
from topo_labels_config import (
    KHARTUM_RULES,
    TOPO_FONT_STYLES,
    load_label_overrides,
)
import matplotlib.patheffects as PathEffects
from shapely.geometry import box


def draw_points_and_labels(
    ax,
    points,
    lines,
    polygons,
    scale,
    map_bbox=None,
    overrides_path="labels.txt",
    symscale=1.0,
    start_pt=None,
):

  txt_overrides, custom_prio = load_label_overrides(overrides_path)
  candidates = []

  edge_margin_m = (1.2 * scale) / 1000.0
  inner_area = (
      map_bbox.buffer(-edge_margin_m)
      if map_bbox is not None
      else None
  )

  for is_node, gdf in [(True, points), (False, polygons), (False, lines)]:
    if gdf is None or gdf.empty:
      continue
    for _, row in gdf.iterrows():
      cat, t1, t2 = classify_feature(row, is_node)
      if cat not in KHARTUM_RULES:
        continue

      prio, font_code, marker, msize, has_icon = KHARTUM_RULES[cat]
      if cat == "amenity_place_of_worship":
        t1_low = t1.lower()
        prio = (
            122
            if ("parrocchia" in t1_low or "parish" in t1_low)
            else (121 if ("chiesa" in t1_low or "church" in t1_low) else 120)
        )
      if (
          cat == "boundary_protected_area"
          and hasattr(row.geometry, "area")
          and row.geometry.area > 5000000
      ):
        font_code = "Text12G"
      if t1 in custom_prio:
        prio = custom_prio[t1]
      if not has_icon and not t1 and not t2:
        continue

      geom = row.geometry
      if inner_area is not None and geom.geom_type in [
          "Polygon",
          "MultiPolygon",
          "LineString",
          "MultiLineString",
      ]:
        geom_clip = geom.intersection(inner_area)
        if not geom_clip.is_empty:
          geom = geom_clip

      pt = (
          geom.interpolate(0.5, normalized=True)
          if geom.geom_type in ["LineString", "MultiLineString"]
          else (
              geom.representative_point()
              if geom.geom_type in ["Polygon", "MultiPolygon"]
              else geom
          )
      )
      x, y = pt.x, pt.y

      for mod in txt_overrides:
        if t1 == mod["name"] and (not mod["icon"] or mod["icon"] == cat):
          x += mod["offsetlon"]
          y += mod["offsetlat"]
          if mod["setlon"] != 0:
            x = mod["setlon"]
          if mod["setlat"] != 0:
            y = mod["setlat"]
          if mod["replacename"]:
            t1 = mod["replacename"]

      candidates.append({
          "cat": cat,
          "prio": prio,
          "x": x,
          "y": y,
          "t1": t1,
          "t2": t2,
          "font": font_code,
          "marker": marker,
          "msize": msize * (symscale ** 2),
          "has_icon": has_icon,
      })

  # Deduplication within 200m
  candidates.sort(key=lambda c: c["prio"], reverse=True)
  dedup = []
  for item in candidates:
    if item["t1"] and any(
        e["t1"] == item["t1"]
        and math.hypot(item["x"] - e["x"], item["y"] - e["y"]) <= 200.0
        for e in dedup
    ):
      item["t1"], item["t2"] = "", ""
      if not item["has_icon"]:
        continue
    dedup.append(item)

  # Collision detection + frame border check
  occ_boxes = []
  if start_pt is not None:
    sx, sy = start_pt
    u = (1.1 * symscale * scale) / 1000.0
    flag_margin = 0.5 * u
    occ_boxes.append(
        box(
            sx - flag_margin,
            sy - flag_margin,
            sx + 3.0 * u + flag_margin,
            sy + 4.2 * u + flag_margin,
        )
    )

  pt_to_m = (0.3527 * scale) / 1000.0
  drawn_count = 0

  for item in dedup:
    x, y = item["x"], item["y"]
    fsize_base, fweight, fstyle, col = TOPO_FONT_STYLES.get(
        item["font"], TOPO_FONT_STYLES["Text4"]
    )
    fsize = fsize_base * symscale
    text = f"{item['t1']}\n{item['t2']}".strip()

    icon_box = None
    if item["has_icon"] and item["marker"]:
      r_m = (math.sqrt(item["msize"]) * 0.45) * pt_to_m
      icon_box = box(x - r_m, y - r_m, x + r_m, y + r_m)
      if inner_area is not None and not inner_area.contains(icon_box):
        continue
      if any(icon_box.intersects(b) for b in occ_boxes):
        continue

    lines_txt = text.split("\n") if text else []
    num_lines = len(lines_txt)
    r_ic_m = (
        (math.sqrt(item["msize"]) * 0.5) * pt_to_m
        if (item["has_icon"] and item["marker"])
        else 0.0
    )

    if item["has_icon"] and item["marker"]:
      y_txt = y + r_ic_m + (0.4 * symscale * scale / 1000.0)
      va_align = "bottom"
    else:
      y_txt = y
      va_align = "center_baseline"

    text_box = None
    if text:
      w_factor = 0.68 if fweight == "bold" else 0.58
      w_m = (max(len(r) for r in lines_txt) * fsize * w_factor * pt_to_m) + (
          0.6 * symscale * pt_to_m
      )
      h_m = (num_lines * fsize * 1.35 * pt_to_m) + (0.4 * symscale * pt_to_m)
      if va_align == "bottom":
        text_box = box(x - w_m / 2, y_txt, x + w_m / 2, y_txt + h_m)
      else:
        text_box = box(
            x - w_m / 2, y_txt - h_m / 2, x + w_m / 2, y_txt + h_m / 2
        )
      if (inner_area is not None and not inner_area.contains(text_box)) or any(
          text_box.intersects(b) for b in occ_boxes
      ):
        text, text_box = "", None

    if not (item["has_icon"] and item["marker"]) and not text:
      continue
    if icon_box:
      occ_boxes.append(icon_box)
    if text_box:
      occ_boxes.append(text_box)

    drawn_count += 1

    if item["has_icon"] and item["marker"]:
      if item["cat"] == "icon_parking":
        ax.scatter(
            x,
            y,
            marker="s",
            color="#0054ff",
            edgecolor="#ffffff",
            s=item["msize"],
            zorder=110,
            linewidths=0.6 * symscale,
        )
        ax.text(
            x,
            y,
            "P",
            color="#ffffff",
            fontsize=4.6 * symscale,
            fontweight="bold",
            ha="center",
            va="center_baseline",
            zorder=111,
        )
      elif item["cat"] == "hospital":
        ax.scatter(
            x,
            y,
            marker="s",
            color="#bf0000",
            edgecolor="#ffffff",
            s=item["msize"],
            zorder=110,
            linewidths=0.6 * symscale,
        )
        r_m = (math.sqrt(item["msize"]) * 0.28) * pt_to_m
        ax.plot(
            [x - r_m, x + r_m],
            [y, y],
            color="#ffffff",
            linewidth=0.75 * symscale,
            solid_capstyle="butt",
            zorder=111,
        )
        ax.plot(
            [x, x],
            [y - r_m, y + r_m],
            color="#ffffff",
            linewidth=0.75 * symscale,
            solid_capstyle="butt",
            zorder=111,
        )
      elif item["cat"] == "helipad":
        ax.scatter(
            x,
            y,
            marker="o",
            color="#000000",
            edgecolor="#ffffff",
            s=item["msize"],
            zorder=110,
            linewidths=0.6 * symscale,
        )
        ax.text(
            x,
            y,
            "H",
            color="#ffffff",
            fontsize=4.5 * symscale,
            fontweight="bold",
            ha="center",
            va="center_baseline",
            zorder=111,
        )
      elif item["cat"] in ("barrier_gate", "barrier"):
        s_ban = max(item["msize"], 28.0 * (symscale ** 2))
        ax.scatter(
            x,
            y,
            marker="o",
            color="#bf0000",
            edgecolor="#ffffff",
            s=s_ban,
            zorder=110,
            linewidths=0.5 * symscale,
        )
        r_m = (math.sqrt(s_ban) * 0.27) * pt_to_m
        ax.plot(
            [x - r_m, x + r_m],
            [y, y],
            color="#ffffff",
            linewidth=0.85 * symscale,
            solid_capstyle="butt",
            zorder=111,
        )
      elif item["cat"] == "aerodrome":
        ax.scatter(
            x,
            y,
            marker="s",
            color="#000000",
            edgecolor="#ffffff",
            s=item["msize"],
            zorder=110,
            linewidths=0.6 * symscale,
        )
        ax.scatter(
            x,
            y,
            marker=item["marker"],
            color="#ffffff",
            s=item["msize"] * 0.48,
            zorder=111,
            linewidths=0.1 * symscale,
        )
      elif item["cat"] == "spring":
        ax.scatter(
            x,
            y,
            marker="o",
            facecolors="none",
            edgecolors=col,
            s=item["msize"],
            zorder=110,
            linewidths=1.05 * symscale,
        )
      else:
        c_ic = "#bf0000" if item["cat"] == "alpine_hut" else col
        lw_ic = 0.0 if item["cat"] == "historic_castle" else 0.95 * symscale
        ax.scatter(
            x,
            y,
            marker=item["marker"],
            color=c_ic,
            s=item["msize"],
            zorder=110,
            linewidths=lw_ic,
        )

    if text:
      t = ax.text(
          x,
          y_txt,
          text,
          fontsize=fsize,
          fontweight=fweight,
          fontstyle=fstyle,
          color=col,
          ha="center",
          va=va_align,
          zorder=115,
      )

      if item["cat"] == "TextHiking3":
        t.set_bbox(
            dict(
                boxstyle="round,pad=0.18",
                facecolor="white",
                edgecolor="#ff0000",
                lw=0.6 * symscale,
            )
        )
      elif item["cat"] == "TextBike3":
        t.set_bbox(
            dict(
                boxstyle="round,pad=0.18",
                facecolor="#ffd166",
                edgecolor="#8e007a",
                lw=0.6 * symscale,
            )
        )
      elif item["cat"] == "TextRoad":
        t.set_bbox(
            dict(
                boxstyle="square,pad=0.18",
                facecolor="#fff65c",
                edgecolor="#000000",
                lw=0.5 * symscale,
            )
        )
      else:
        t.set_path_effects([
            PathEffects.withStroke(
                linewidth=1.4 * symscale, foreground="white"
            )
        ])
  print(
      f"  Labels/icons drawn: {drawn_count} (out of {len(dedup)} OSM candidates)",
      flush=True,
  )
