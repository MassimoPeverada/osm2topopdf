from matplotlib.legend_handler import HandlerBase
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Rectangle
import matplotlib.patheffects as PathEffects
from matplotlib.text import Text
from topo_symbols import TOPO_MARKERS


class _BoxSymbol:

  def __init__(self, shape, facecolor, letter, textcolor="#ffffff"):
    self.shape = shape
    self.facecolor = facecolor
    self.letter = letter
    self.textcolor = textcolor


class _TrackNormSymbol:

  def __init__(self, label):
    self.label = label


class _HandlerTrackNormSymbol(HandlerBase):

  def create_artists(
      self,
      legend,
      orig_handle,
      xdescent,
      ydescent,
      width,
      height,
      fontsize,
      trans,
  ):
    cy = ydescent + height * 0.5
    dy = height * 0.22
    x0, x1 = xdescent, xdescent + width
    bg = Line2D([x0, x1], [cy, cy], color="#ffffff", lw=1.4, transform=trans)
    top_edge = Line2D(
        [x0, x1], [cy + dy, cy + dy], color="#000000", lw=0.55, transform=trans
    )
    bot_edge = Line2D(
        [x0, x1],
        [cy - dy, cy - dy],
        color="#000000",
        lw=0.55,
        ls=(0, (3.2, 1.8)),
        transform=trans,
    )
    return [bg, top_edge, bot_edge]


class _TrackRoughSymbol:

  def __init__(self, label):
    self.label = label


class _HandlerTrackRoughSymbol(HandlerBase):

  def create_artists(
      self,
      legend,
      orig_handle,
      xdescent,
      ydescent,
      width,
      height,
      fontsize,
      trans,
  ):
    cy = ydescent + height * 0.5
    dy = height * 0.22
    x0, x1 = xdescent, xdescent + width
    bg = Line2D([x0, x1], [cy, cy], color="#ffffff", lw=1.4, transform=trans)
    top_edge = Line2D(
        [x0, x1],
        [cy + dy, cy + dy],
        color="#000000",
        lw=0.55,
        ls=(0, (3.0, 1.8)),
        transform=trans,
    )
    bot_edge = Line2D(
        [x0, x1],
        [cy - dy, cy - dy],
        color="#000000",
        lw=0.55,
        ls=(0, (3.0, 1.8)),
        transform=trans,
    )
    return [bg, top_edge, bot_edge]


class _FunicularSymbol:

  def __init__(self, label):
    self.label = label


class _HandlerFunicularSymbol(HandlerBase):

  def create_artists(
      self,
      legend,
      orig_handle,
      xdescent,
      ydescent,
      width,
      height,
      fontsize,
      trans,
  ):
    cy = ydescent + height * 0.5
    x0, x1 = xdescent, xdescent + width
    line = Line2D([x0, x1], [cy, cy], color="#000000", lw=0.85, transform=trans)
    ticks = Line2D(
        [x0, x1],
        [cy, cy],
        color="#000000",
        lw=2.8,
        ls=(0, (0.6, 2.4)),
        solid_capstyle="butt",
        transform=trans,
    )
    return [line, ticks]


class _DamSymbol:

  def __init__(self, label):
    self.label = label


class _HandlerDamSymbol(HandlerBase):

  def create_artists(
      self,
      legend,
      orig_handle,
      xdescent,
      ydescent,
      width,
      height,
      fontsize,
      trans,
  ):
    cy = ydescent + height * 0.58
    x0, x1 = xdescent, xdescent + width
    line = Line2D(
        [x0, x1],
        [cy, cy],
        color="#000000",
        lw=1.1,
        solid_capstyle="butt",
        transform=trans,
    )
    teeth = Line2D(
        [x0, x1],
        [cy - height * 0.22, cy - height * 0.22],
        color="#000000",
        lw=1.5,
        ls=(0, (1.2, 2.4)),
        solid_capstyle="butt",
        transform=trans,
    )
    return [line, teeth]


class _HandlerBoxSymbol(HandlerBase):

  def create_artists(
      self,
      legend,
      orig_handle,
      xdescent,
      ydescent,
      width,
      height,
      fontsize,
      trans,
  ):
    cx = xdescent + width * 0.5
    cy = ydescent + height * 0.5
    side = min(width, height) * 1.05
    if orig_handle.shape == "circle":
      patch = Circle(
          (cx, cy),
          radius=side * 0.52,
          facecolor=orig_handle.facecolor,
          edgecolor="#ffffff",
          linewidth=0.4,
          transform=trans,
      )
    else:
      patch = Rectangle(
          (cx - side * 0.5, cy - side * 0.5),
          side,
          side,
          facecolor=orig_handle.facecolor,
          edgecolor="#ffffff",
          linewidth=0.4,
          transform=trans,
      )
    if orig_handle.letter == "AIRPLANE":
      air_side = fontsize * 1.25
      patch_air = Rectangle(
          (cx - air_side * 0.5, cy - air_side * 0.5),
          air_side,
          air_side,
          facecolor="#000000",
          edgecolor="#000000",
          linewidth=0.4,
          transform=trans,
      )
      plane = Line2D(
          [cx],
          [cy],
          marker=TOPO_MARKERS["airplane"],
          color="none",
          markerfacecolor="#ffffff",
          markeredgecolor="#ffffff",
          markersize=air_side * 0.78,
          transform=trans,
      )
      return [patch_air, plane]

    if orig_handle.letter == "+":
      r_cross = side * 0.28
      cross_h = Line2D(
          [cx - r_cross, cx + r_cross],
          [cy, cy],
          color="#ffffff",
          lw=0.75,
          solid_capstyle="butt",
          transform=trans,
      )
      cross_v = Line2D(
          [cx, cx],
          [cy - r_cross, cy + r_cross],
          color="#ffffff",
          lw=0.75,
          solid_capstyle="butt",
          transform=trans,
      )
      return [patch, cross_h, cross_v]

    if orig_handle.letter == "-":
      r_bar = side * 0.27
      bar = Line2D(
          [cx - r_bar, cx + r_bar],
          [cy, cy],
          color="#ffffff",
          lw=0.80,
          solid_capstyle="butt",
          transform=trans,
      )
      return [patch, bar]

    txt = Text(
        cx,
        cy - fontsize * 0.06,
        orig_handle.letter,
        color=orig_handle.textcolor,
        fontsize=fontsize * 0.88,
        fontweight="bold",
        ha="center",
        va="center_baseline",
        transform=trans,
    )
    return [patch, txt]


class _AerialwaySymbol:

  def __init__(self, label):
    self.label = label


class _HandlerAerialwaySymbol(HandlerBase):

  def create_artists(
      self,
      legend,
      orig_handle,
      xdescent,
      ydescent,
      width,
      height,
      fontsize,
      trans,
  ):
    cy = ydescent + height * 0.5
    x0 = xdescent
    x1 = xdescent + width
    base_line = Line2D(
        [x0, x1], [cy, cy], color="#000000", lw=0.65, transform=trans
    )
    squares = Line2D(
        [x0, x1],
        [cy, cy],
        color="#000000",
        lw=2.3,
        ls=(0, (0.8, 3.8)),
        transform=trans,
    )
    return [base_line, squares]


class _RailwaySymbol:

  def __init__(self, label):
    self.label = label


class _HandlerRailwaySymbol(HandlerBase):

  def create_artists(
      self,
      legend,
      orig_handle,
      xdescent,
      ydescent,
      width,
      height,
      fontsize,
      trans,
  ):
    cy = ydescent + height * 0.5
    x0 = xdescent
    x1 = xdescent + width
    black_edge = Line2D(
        [x0, x1],
        [cy, cy],
        color="#000000",
        lw=1.45,
        solid_capstyle="butt",
        transform=trans,
    )
    white_dashes = Line2D(
        [x0, x1],
        [cy, cy],
        color="#ffffff",
        lw=0.90,
        ls=(0, (3.2, 3.2)),
        solid_capstyle="butt",
        transform=trans,
    )
    return [black_edge, white_dashes]


class _FlagSymbol:

  def __init__(self, label):
    self.label = label


class _HandlerFlagSymbol(HandlerBase):

  def create_artists(
      self,
      legend,
      orig_handle,
      xdescent,
      ydescent,
      width,
      height,
      fontsize,
      trans,
  ):
    h_tot = fontsize * 1.25
    u = h_tot * 0.28
    x0 = xdescent + width * 0.5 - u * 1.4
    y0 = ydescent + height * 0.5 - h_tot * 0.5
    artists = [
        Line2D(
            [x0, x0],
            [y0, y0 + h_tot],
            color="#000000",
            lw=1.1,
            transform=trans,
        )
    ]
    for col_i in range(3):
      for row_i in range(2):
        sq_col = "#000000" if (col_i + row_i) % 2 == 1 else "#ffffff"
        artists.append(
            Rectangle(
                (x0 + col_i * u, y0 + h_tot - (row_i + 1) * u),
                u,
                u,
                facecolor=sq_col,
                edgecolor="#000000",
                linewidth=0.4,
                transform=trans,
            )
        )
    return artists


def compute_legend_layout(map_h_mm=0.0):
  if map_h_mm >= 198.0:
    return {
        "ncol": 1,
        "w_mm": 64.0,
        "h_mm": map_h_mm,
        "font": 4.85,
        "spacing": 0.38,
    }
  return {
      "ncol": 2,
      "w_mm": 98.0,
      "h_mm": max(map_h_mm, 138.0),
      "font": 4.55,
      "spacing": 0.38,
  }


def _legend_road(col_fill, lw_fill, lw_border, label, ls="-", alpha=1.0):
  line = Line2D(
      (0,), (0,), color=col_fill, lw=lw_fill, ls=ls, alpha=alpha, label=label
  )
  line.set_path_effects(
      [PathEffects.withStroke(linewidth=lw_border, foreground="#000000")]
  )
  return line
def draw_legend(
    ax_l,
    map_title,
    scale,
    layout,
    strings,
    author="",
    date_str="",
    credits_text="",
    utm_label="UTM 32N",
    version="1.1.7",
    dtmmain=100,
    dtmsec=25,
):

  z = (0,)

  items = [
      Line2D(z, z, color="#d90429", lw=2.4, label=strings["legend_itinerary"]),
      _FlagSymbol(strings["legend_start"]),
      Line2D(
          z,
          z,
          color="#d90429",
          lw=2.1,
          ls=(0, (3.2, 2.2)),
          label=strings["legend_variant"],
      ),
      Line2D(
          z,
          z,
          color="#e60000",
          lw=1.8,
          alpha=0.55,
          label=strings["legend_hiking_route"],
      ),
      Line2D(
          z,
          z,
          color="#8e007a",
          lw=1.8,
          alpha=0.55,
          label=strings["legend_bike_route"],
      ),
      _legend_road("#e890a0", 2.0, 2.8, strings["legend_motorway"]),
      _legend_road(
          "#e890a0",
          2.0,
          2.8,
          strings["legend_motorway_tunnel"],
          ls=(0, (2, 2)),
          alpha=0.75,
      ),
      _legend_road("#fff65c", 1.7, 2.4, strings["legend_major_road"]),
      _legend_road(
          "#fff65c",
          1.7,
          2.4,
          strings["legend_major_road_tunnel"],
          ls=(0, (2, 2)),
          alpha=0.75,
      ),
      _legend_road("#ffffff", 1.0, 1.45, strings["legend_local_road"]),
      _legend_road(
          "#ffffff",
          1.0,
          1.45,
          strings["legend_local_road_tunnel"],
          ls=(0, (2, 2)),
          alpha=0.75,
      ),
      _TrackNormSymbol(strings["legend_track_norm"]),
      _TrackRoughSymbol(strings["legend_track_rough"]),
      Line2D(
          z,
          z,
          color="#000000",
          lw=0.6,
          ls=(0, (2.5, 2.5)),
          label=strings["legend_footpath"],
      ),
      Line2D(
          z,
          z,
          color="#0054ff",
          lw=0.9,
          ls=(0, (2.5, 2.1)),
          label=strings["legend_cycleway"],
      ),
      _RailwaySymbol(strings["legend_railway"]),
      _AerialwaySymbol(strings["legend_aerialway"]),
      _DamSymbol(strings["legend_dam"]),
      Line2D(z, z, color="#5cc2d1", lw=0.9, label=strings["legend_waterway"]),
      Line2D(
          z,
          z,
          color="#c85a00",
          lw=0.65,
          label=strings["legend_contour_major"].format(dtmmain=dtmmain),
      ),
      Line2D(
          z,
          z,
          color="#d98a2b",
          lw=0.3,
          alpha=0.65,
          label=strings["legend_contour_minor"].format(dtmsec=dtmsec),
      ),

      Patch(
          facecolor="#80ed99",
          alpha=0.35,
          edgecolor="#007f5f",
          linewidth=1.2,
          linestyle=(0, (5, 2, 1.5, 2)),
          label=strings["legend_park"],
      ),
      Patch(facecolor="#ace5b6", edgecolor="none", label=strings["legend_forest"]),
      Patch(facecolor="#dff0cf", edgecolor="none", label=strings["legend_meadow"]),
      Patch(
          facecolor="#f2fae3",
          edgecolor="#d8e2c8",
          label=strings["legend_farmland"],
      ),
      Patch(facecolor="#d8e8c8", edgecolor="none", label=strings["legend_scrub"]),
      Patch(
          facecolor="#f7e7b4", edgecolor="#e0c989", label=strings["legend_sand"]
      ),
      Patch(
          facecolor="#e0fbfc", edgecolor="#90e0ef", label=strings["legend_glacier"]
      ),
      Patch(
          facecolor="#e6dedb", edgecolor="#b5aca9", label=strings["legend_rock"]
      ),
      Patch(
          facecolor="#bae8ff", edgecolor="#5cc2d1", label=strings["legend_water"]
      ),
      Patch(
          facecolor="#cdeef7", edgecolor="#7cc6de", label=strings["legend_wetland"]
      ),
      Patch(
          facecolor="#d9f2d9",
          edgecolor="#52b788",
          label=strings["legend_sports"],
      ),
      Patch(facecolor="#c9d6c8", edgecolor="#6c757d", label=strings["legend_cemetery"]),
      Patch(
          facecolor="#f5d0d0",
          edgecolor="#c9184a",
          linestyle=(0, (4, 2)),
          label=strings["legend_military"],
      ),
      Patch(facecolor="#c2995d", edgecolor="#2b2d42", label=strings["legend_building"]),
      Patch(
          facecolor="#d1d1d1", edgecolor="none", label=strings["legend_urban"]
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["church"],
          color="w",
          markeredgecolor="#000",
          markerfacecolor="#000",
          markersize=5.5,
          label=strings["legend_church"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["train"],
          color="w",
          markeredgecolor="#000",
          markerfacecolor="#000",
          markersize=5.5,
          label=strings["legend_station"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["castle"],
          color="w",
          markeredgecolor="none",
          markeredgewidth=0.0,
          markerfacecolor="#000000",
          markersize=6.2,
          label=strings["legend_castle"],
      ),
      _BoxSymbol("square", "#bf0000", "+"),
      _BoxSymbol("square", "#000000", "AIRPLANE"),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["viewpoint"],
          color="w",
          markeredgecolor="#000",
          markersize=5.5,
          label=strings["legend_viewpoint"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["alpine_hut"],
          color="w",
          markerfacecolor="#bf0000",
          markeredgecolor="#bf0000",
          markersize=5.5,
          label=strings["legend_alpine_hut"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["golf"],
          color="w",
          markeredgecolor="#006100",
          markersize=5.5,
          label=strings["legend_golf"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["tent"],
          color="w",
          markeredgecolor="#000",
          markersize=5.5,
          label=strings["legend_camp_site"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["landfill"],
          color="w",
          markeredgecolor="#000",
          markersize=5.5,
          label=strings["legend_landfill"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["quarry"],
          color="w",
          markeredgecolor="#000",
          markersize=4.5,
          label=strings["legend_quarry"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["antenna"],
          color="w",
          markeredgecolor="#000",
          markersize=5.5,
          label=strings["legend_tower"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["wayside_cross"],
          color="w",
          markeredgecolor="#000",
          markersize=5,
          label=strings["legend_wayside_cross"],
      ),
      Line2D(
          z,
          z,
          marker="^",
          color="w",
          markerfacecolor="#000",
          markersize=4.5,
          label=strings["legend_peak"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["saddle"],
          color="w",
          markeredgecolor="#000",
          markersize=5.5,
          label=strings["legend_saddle"],
      ),
      _BoxSymbol("square", "#0054ff", "P"),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["drop"],
          color="w",
          markerfacecolor="#0054ff",
          markeredgecolor="#0054ff",
          markersize=5,
          label=strings["legend_fountain"],
      ),
      Line2D(
          z,
          z,
          marker="o",
          color="w",
          markerfacecolor="none",
          markeredgecolor="#0054ff",
          markeredgewidth=1.05,
          markersize=4.5,
          label=strings["legend_spring"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["ford"],
          color="w",
          markeredgecolor="#0054ff",
          markersize=5,
          label=strings["legend_ford"],
      ),
      Line2D(
          z,
          z,
          marker=TOPO_MARKERS["cave"],
          color="w",
          markeredgecolor="#000",
          markersize=5,
          label=strings["legend_cave"],
      ),
      _BoxSymbol("circle", "#bf0000", "-"),
      Line2D(
          z,
          z,
          marker="o",
          color="w",
          markerfacecolor="#000",
          markersize=4,
          label=strings["legend_poi"],
      ),
      _BoxSymbol("circle", "#000000", "H"),
  ]

  labels = []
  for v in items:
    if isinstance(v, _BoxSymbol):
      if v.letter == "+":
        labels.append(strings["legend_hospital"])
      elif v.letter == "P":
        labels.append(strings["legend_parking"])
      elif v.letter == "H":
        labels.append(strings["legend_helipad"])
      elif v.letter == "-":
        labels.append(strings["legend_gate"])
      elif v.letter == "AIRPLANE":
        labels.append(strings["legend_aerodrome"])
    elif isinstance(
        v,
        (
            _TrackNormSymbol,
            _TrackRoughSymbol,
            _AerialwaySymbol,
            _FlagSymbol,
            _RailwaySymbol,
            _FunicularSymbol,
            _DamSymbol,
        ),
    ):
      labels.append(v.label)
    else:
      labels.append(v.get_label())

  ax_l.text(0.0, 0.992, map_title, fontsize=9.0, fontweight="bold", va="top")
  scale_str = f"{scale:,}"
  ax_l.text(
      0.0,
      0.964,
      f"{strings['scale_prefix']}{scale_str}",
      fontsize=7.2,
      fontweight="bold",
      va="top",
  )

  meta_info = []
  if author:
    meta_info.append(f"{strings['author_prefix']} {author}")
  if date_str:
    meta_info.append(f"{strings['date_prefix']} {date_str}")

  y_legend = 0.930
  if meta_info:
    ax_l.text(
        0.0,
        0.938,
        "  |  ".join(meta_info),
        fontsize=5.2,
        color="#222222",
        va="top",
    )
    y_legend = 0.916
  ax_l.legend(
      handles=items,
      labels=labels,
      handler_map={
          _BoxSymbol: _HandlerBoxSymbol(),
          _TrackNormSymbol: _HandlerTrackNormSymbol(),
          _TrackRoughSymbol: _HandlerTrackRoughSymbol(),
          _AerialwaySymbol: _HandlerAerialwaySymbol(),
          _FlagSymbol: _HandlerFlagSymbol(),
          _RailwaySymbol: _HandlerRailwaySymbol(),
          _FunicularSymbol: _HandlerFunicularSymbol(),
          _DamSymbol: _HandlerDamSymbol(),
      },
      loc="upper left",
      bbox_to_anchor=(-0.02, y_legend),
      ncol=layout["ncol"],
      columnspacing=0.65,
      handlelength=1.4,
      handletextpad=0.45,
      frameon=False,
      fontsize=layout["font"],
      labelspacing=layout["spacing"],
  )

  credits = credits_text.strip() or strings["default_credits"].format(
      version=version, dtmsec=dtmsec, utm=utm_label
  )

  ax_l.text(
      0.0,
      0.005,
      credits,
      fontsize=5.2,
      color="#111111",
      va="bottom",
      linespacing=1.28,
  )
