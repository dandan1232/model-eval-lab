# Procedural reconstruction for Blender 5.0 (bpy + bmesh, self-contained, no external files).
# Target: white cat-eared pixel-display desktop clock / speaker (single 4K reference image).
#
# OBSERVATIONS FROM THE REFERENCE (one front view, camera ~3 deg above the horizontal and
# almost orthographic; 3840 x 2160 px; body width = 2161 px = 1.0 model unit; z up, -Y = front):
# * Category: compact "cat robot" pixel clock / Bluetooth speaker, Divoom-Ditoo-like.
# * Body: soft rounded cushion, wider than tall (1.00 wide x 0.75 tall x ~0.60 deep, depth is
#   inferred), flat front face carrying a large glossy black rounded-rectangle display.
# * Silhouette: straight vertical sides from z~0.23 to z~0.59; the lower sides sweep inward
#   along a large circular arc (R~0.21, front view) onto a narrower rounded plinth (height
#   ~0.056) that is split from the shell by a thin dark parting line.  Top left/right corners
#   are broadly rounded (R~0.175) and flow continuously into the outer flanks of the ears.
# * Ears: two white ears on the top back corners.  Outer flank convex (arc R~0.33), inner
#   flank slightly concave (arc R~0.56), rounded tip (R~0.047), apex ~0.13 above the top
#   surface at x = -0.379 / +0.371; the outer flank meets the body side ~0.09 below the top.
# * Top controls on the front half of the top face: three low white puck buttons (diameter
#   ~0.137, centres x = -0.326 / -0.153 / +0.020), a tiny white status LED (x = +0.136) and a
#   silver knurled knob (diameter ~0.18, x = +0.293, ~0.045 tall, ~100 straight flutes, flat
#   brushed top with a bright chamfer, dark shadow line underneath).
# * Display: black glass panel (0.788 x 0.574, corner radius ~0.12; margins ~0.106 left/right,
#   ~0.078 top, ~0.041 down to the seam) with a black hairline rim, a grey reflective band just
#   inside the rim (wider along the bottom edge), and warm cream emissive pixel art: two chunky
#   pixel "0" eyes (4 x 6 cells, the 1 x 2 cell hole sits left of centre in BOTH eyes), two dim
#   grey squares and one cream square (half a cell higher) above the nose, a short stair-stepped
#   diagonal mouth stroke, and "dissolving" blush (larger + smaller square) under each eye.
# * Three tiny dark slots sit on the top face between / behind the buttons.
# * Materials: warm off-white plastic with a soft sheen (ears, buttons and body identical),
#   black rubber feet under the front edge, polished stainless knob, matte cream emissive
#   pixels.  No labels or text; no transparency besides the glass-like screen.
#
# ASSUMPTIONS (not visible in the reference): depth ~0.60 of the width, four feet in a
#   rectangle, flat back with the same cushion profile, ears slightly flattened front-to-back,
#   top corner rounding is strongest at the back (where the ears continue it) so that the
#   controls sit on a flat top.
#
# RESULT: one watertight mesh object "CatRobot" at the origin (feet on z = 0), ~28k vertices,
#   10 materials, built in well under a second; no camera, light, floor or render is created.

import math

import bpy
import bmesh
from mathutils import Vector


# ----------------------------------------------------------------------------- utilities
def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def smooth(t):
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def srgb(c):
    """sRGB (0..1) -> linear, for node colour sockets."""
    return tuple((v / 12.92) if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


# ------------------------------------------------------------------- reference -> world
PX = 2161.0      # reference pixels per model unit (body width)
XC = 1918.5      # reference x of the body centre line
YB = 2010.0      # reference y of the body bottom front edge
ZB = 0.021       # world height of that edge (rubber feet sit below it)


def ux(x):
    """reference pixel x -> world x"""
    return (x - XC) / PX


def uz(y):
    """reference pixel y -> world z"""
    return ZB + (YB - y) / PX


# ---------------------------------------------------------------------- main dimensions
HALF_D = 0.30                      # half depth (inferred)
Z_BOT = ZB                         # bottom of the plastic body
Z_SEAM = uz(1888.0)                # ~0.077  shell / plinth parting line
Z_TOP = uz(392.0)                  # ~0.770  top surface
SEAM_GAP = 0.0012
R_VERT = 0.080                     # plan-view corner radius of the cushion
R_BOT_X = 0.208                    # large lower sweep of the left/right sides
PLINTH_INSET = 0.0656              # shell inset at the seam (= plinth inset, all round)
R_BOT_Y = 0.040                    # height over which front/back blend into that inset
R_TOP_X = 0.175                    # top left/right corner rounding (at the back)
R_TOP_Y = 0.030                    # front/back top edge rounding
G_FRONT = 0.45                     # fraction of the top rounding kept at the front face
BASE_FILLET = 0.016

# top controls (centre x, centre y)
BUTTON_R = 0.0687
BUTTON_H = 0.038
BUTTON_FILLET = 0.006
MARKS = [(ux(1392.0), -0.025), (ux(1738.0), -0.025), (ux(2093.0), -0.025)]   # tiny slots on top
BUTTONS = [(ux(1215.0), -0.150), (ux(1587.0), -0.150), (ux(1962.0), -0.150)]
LED = (ux(2212.0), -0.150)
KNOB = (ux(2547.0), -0.030)
KNOB_R = 0.0895
KNOB_H = 0.046
KNOB_CHAMFER = 0.0045
KNOB_FLUTES = 96
KNOB_DEPTH = 0.0022

# ears
EAR_Y = 0.155                      # depth position of the ear axis (toward the back)
EAR_DEPTH = 0.85                   # front-to-back flattening of the ear cross-sections
EAR_APEX_X = (-0.3787, 0.3707)     # apex x of the left / right ear

# feet
FOOT_R = 0.0345
FOOT_X, FOOT_Y = 0.33, 0.165

# display (outline of the dark glass panel incl. its black hairline rim)
DISP_A = 0.5 * (ux(2772.0) - ux(1070.0))        # ~0.394 half width
DISP_B = 0.5 * (uz(559.0) - uz(1800.0))         # ~0.287 half height
DISP_CZ = 0.5 * (uz(559.0) + uz(1800.0))        # centre height
DISP_R = 0.122                                   # corner radius
DISP_HAIRLINE = 0.0022             # dark hairline gap between body and glass
DISP_BEVEL = 0.0085                # grey reflective band inside the glass rim

SHARP_ANGLE = math.radians(35.0)
OBJ_NAME = "CatRobot"


# -------------------------------------------------------------------------- scene reset
def reset_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for store in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras,
                  bpy.data.curves, bpy.data.metaballs, bpy.data.armatures, bpy.data.lattices):
        for item in list(store):
            if item.users == 0:
                store.remove(item)


# ------------------------------------------------------------------------- materials
def make_material(name, color, rough, metal=0.0, spec=0.5, coat=0.0, coat_rough=0.03,
                  emit=None, emit_strength=0.0, bump=0.0, aniso=0.0):
    mat = bpy.data.materials.new(name)
    nt = mat.node_tree
    if nt is None:
        try:
            mat.use_nodes = True
        except Exception:
            pass
        nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    if out is None:
        out = nt.nodes.new("ShaderNodeOutputMaterial")
    if not out.inputs["Surface"].is_linked:
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    def seti(key, val):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = val

    seti("Base Color", (*srgb(color), 1.0))
    seti("Roughness", rough)
    seti("Metallic", metal)
    seti("Specular IOR Level", spec)
    seti("Coat Weight", coat)
    seti("Coat Roughness", coat_rough)
    if emit is not None:
        seti("Emission Color", (*srgb(emit), 1.0))
        seti("Emission Strength", emit_strength)

    if bump > 0.0:
        # very fine moulded-plastic micro texture
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 700.0
        noise.inputs["Detail"].default_value = 2.0
        noise.inputs["Roughness"].default_value = 0.6
        bmp = nt.nodes.new("ShaderNodeBump")
        bmp.inputs["Strength"].default_value = bump
        bmp.inputs["Distance"].default_value = 0.002
        nt.links.new(noise.outputs["Fac"], bmp.inputs["Height"])
        nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])

    if aniso > 0.0 and "Tangent" in bsdf.inputs:
        # circular brushed top: circumferential tangent + fine ring pattern in the roughness
        tan = nt.nodes.new("ShaderNodeTangent")
        tan.direction_type = "RADIAL"
        tan.axis = "Z"
        nt.links.new(tan.outputs["Tangent"], bsdf.inputs["Tangent"])
        seti("Anisotropic", aniso)
        coord = nt.nodes.new("ShaderNodeTexCoord")
        wave = nt.nodes.new("ShaderNodeTexWave")
        wave.wave_type = "RINGS"
        try:
            wave.rings_direction = "Z"
        except Exception:
            pass
        wave.inputs["Scale"].default_value = 260.0
        wave.inputs["Distortion"].default_value = 3.0
        wave.inputs["Detail"].default_value = 2.0
        wave.inputs["Detail Scale"].default_value = 4.0
        nt.links.new(coord.outputs["Object"], wave.inputs["Vector"])
        ramp = nt.nodes.new("ShaderNodeMapRange")
        ramp.inputs["From Min"].default_value = 0.0
        ramp.inputs["From Max"].default_value = 1.0
        ramp.inputs["To Min"].default_value = max(rough - 0.07, 0.03)
        ramp.inputs["To Max"].default_value = rough + 0.07
        nt.links.new(wave.outputs["Fac"], ramp.inputs["Value"])
        nt.links.new(ramp.outputs["Result"], bsdf.inputs["Roughness"])
    return mat


MAT_WHITE = 0      # body, ears, buttons
MAT_DARK = 1       # rubber feet, seam, knob base
MAT_BEZEL = 2      # hairline rim of the display
MAT_SCREEN = 3
MAT_BEVEL = 4      # grey band inside the display rim
MAT_CREAM = 5
MAT_GRAY = 6
MAT_STEEL = 7
MAT_KNOBTOP = 8
MAT_LED = 9


def build_materials():
    # Pixel emission strengths are tuned for Blender's default AgX view transform; the LED
    # pixels must be driven well above 1.0 to read as bright warm cream instead of grey.
    return [
        make_material("WhitePlastic", (0.925, 0.912, 0.893), 0.30, spec=0.55, bump=0.03),
        make_material("DarkRubber", (0.022, 0.022, 0.022), 0.60, spec=0.35),
        make_material("BezelDark", (0.010, 0.010, 0.010), 0.30, spec=0.3),
        make_material("ScreenGlass", (0.003, 0.003, 0.003), 0.12, spec=0.35, coat=0.6, coat_rough=0.03),
        make_material("ScreenBevel", (0.22, 0.215, 0.21), 0.25, spec=0.6, coat=0.5, coat_rough=0.05),
        make_material("PixelCream", (0.0, 0.0, 0.0), 0.6, spec=0.2, emit=(1.0, 0.89, 0.68),
                      emit_strength=4.0),
        make_material("PixelGrey", (0.0, 0.0, 0.0), 0.6, spec=0.2, emit=(0.37, 0.365, 0.36),
                      emit_strength=1.0),
        make_material("KnobSteel", (0.83, 0.82, 0.81), 0.20, metal=1.0),
        make_material("KnobTopSteel", (0.83, 0.82, 0.81), 0.33, metal=1.0, aniso=0.6),
        make_material("LedWhite", (0.96, 0.95, 0.93), 0.18, spec=0.6, emit=(1.0, 1.0, 1.0),
                      emit_strength=0.35),
    ]


# ------------------------------------------------------------------- mesh construction
class Builder:
    """Accumulates every part into one bmesh; faces carry a material index."""

    def __init__(self):
        self.bm = bmesh.new()

    def v(self, x, y, z):
        return self.bm.verts.new((x, y, z))

    def f(self, verts, mat):
        face = self.bm.faces.new(verts)
        face.material_index = mat
        face.smooth = True
        return face


def loft(Bd, loops, mat):
    """Bridge consecutive closed loops with quads (all loops share the same point count)."""
    for A, C in zip(loops[:-1], loops[1:]):
        n = len(A)
        for j in range(n):
            k = j + 1 if j + 1 < n else 0
            Bd.f((A[j], A[k], C[k], C[j]), mat)


def cap(Bd, loop, center, mat, rings=4):
    """Close a planar loop with concentric scaled rings and a centre fan."""
    c = Vector(center)
    prev = loop
    n = len(loop)
    for i in range(1, rings + 1):
        s = 1.0 - i / (rings + 1.0)
        nxt = [Bd.bm.verts.new(c + (v.co - c) * s) for v in loop]
        loft(Bd, [prev, nxt], mat)
        prev = nxt
    cv = Bd.bm.verts.new(c)
    for j in range(n):
        Bd.f((prev[j], prev[j + 1 if j + 1 < n else 0], cv), mat)


def rr2d(a, b, r, m=12, k=10):
    """Rounded-rectangle outline centred on the origin, counter-clockwise, as (u, v)."""
    r = max(min(r, a * 0.985, b * 0.985), 1e-5)
    ax, by = a - r, b - r
    pts = []
    for j in range(m):                                   # right edge, upwards
        pts.append((a, -by + 2.0 * by * j / m))
    for j in range(k):                                   # top-right corner arc
        t = 0.5 * math.pi * j / k
        pts.append((ax + r * math.cos(t), by + r * math.sin(t)))
    for j in range(m):                                   # top edge, leftwards
        pts.append((ax - 2.0 * ax * j / m, b))
    for j in range(k):                                   # top-left corner arc
        t = 0.5 * math.pi * j / k
        pts.append((-ax - r * math.sin(t), by + r * math.cos(t)))
    for j in range(m):                                   # left edge, downwards
        pts.append((-a, by - 2.0 * by * j / m))
    for j in range(k):                                   # bottom-left corner arc
        t = 0.5 * math.pi * j / k
        pts.append((-ax - r * math.cos(t), -by - r * math.sin(t)))
    for j in range(m):                                   # bottom edge, rightwards
        pts.append((-ax + 2.0 * ax * j / m, -b))
    for j in range(k):                                   # bottom-right corner arc
        t = 0.5 * math.pi * j / k
        pts.append((ax + r * math.sin(t), -by - r * math.cos(t)))
    return pts


def lathe(Bd, prof, n, mat, cx=0.0, cy=0.0):
    """Surface of revolution around a vertical axis; prof = [(radius, z), ...] bottom->top.
    A radius of 0 is allowed at the ends and becomes a single pole vertex."""
    ang = [2.0 * math.pi * i / n for i in range(n)]
    rings = []
    for r, z in prof:
        if r <= 1e-9:
            rings.append(Bd.v(cx, cy, z))
        else:
            rings.append([Bd.v(cx + r * math.cos(a), cy + r * math.sin(a), z) for a in ang])
    for A, C in zip(rings[:-1], rings[1:]):
        a_ring, c_ring = isinstance(A, list), isinstance(C, list)
        for j in range(n):
            k = j + 1 if j + 1 < n else 0
            if a_ring and c_ring:
                Bd.f((A[j], A[k], C[k], C[j]), mat)
            elif a_ring:
                Bd.f((A[j], A[k], C), mat)
            else:
                Bd.f((A, C[k], C[j]), mat)
    return rings


def arc_inset(d, R):
    """Inset of a circular rounding; d = distance from the tangent point with the flat face."""
    d = clamp(d, 0.0, R)
    return R - math.sqrt(max(R * R - d * d, 0.0))


def ell_inset(d, height, inset):
    """Quarter-ellipse blend along the flat face: full inset (horizontal tangent) at d = 0,
    zero inset (vertical tangent) at d = height.  Keeps the face flat almost to the seam."""
    v = 1.0 - clamp(d / height, 0.0, 1.0)
    return inset * (1.0 - math.sqrt(max(1.0 - v * v, 0.0)))


def merge_levels(zs, lo, hi, min_step=0.0006):
    zs = sorted(clamp(z, lo, hi) for z in zs)
    out = []
    for z in zs:
        if not out or z - out[-1] > min_step:
            out.append(z)
    if out[-1] < hi - 1e-9:
        out.append(hi)
    return out


# ------------------------------------------------------------------------ body shell
def shell_half_sizes(z):
    """Half width / half depth of the shell cross-section at height z."""
    ix = arc_inset((Z_BOT + R_BOT_X) - z, R_BOT_X) + arc_inset(z - (Z_TOP - R_TOP_X), R_TOP_X)
    iy = ell_inset(z - Z_SEAM, R_BOT_Y, PLINTH_INSET) + arc_inset(z - (Z_TOP - R_TOP_Y), R_TOP_Y)
    return 0.5 - ix, HALF_D - iy


def top_round_gain(y):
    """Strength of the top corner rounding along the depth: gentle at the front so the controls
    sit on a flat top, full strength toward the back where the ears continue the corner."""
    return G_FRONT + (1.0 - G_FRONT) * smooth((y - 0.07) / 0.10)


def add_shell(Bd):
    zs = [Z_SEAM, Z_TOP]
    zt = Z_BOT + R_BOT_X                                   # lower side sweep
    ph = math.asin(clamp((zt - Z_SEAM) / R_BOT_X, 0.0, 1.0))
    zs += [zt - R_BOT_X * math.sin(ph * j / 26.0) for j in range(27)]
    zt = Z_SEAM + R_BOT_Y                                   # lower front/back blend
    zs += [zt - R_BOT_Y * (1.0 - j / 16.0) ** 1.6 for j in range(17)]
    zt = Z_TOP - R_TOP_X                                    # top corners
    zs += [zt + R_TOP_X * math.sin(0.5 * math.pi * j / 36.0) for j in range(37)]
    zt = Z_TOP - R_TOP_Y                                    # top edge fillet
    zs += [zt + R_TOP_Y * math.sin(0.5 * math.pi * j / 12.0) for j in range(13)]
    z0, z1 = Z_BOT + R_BOT_X, Z_TOP - R_TOP_X               # straight middle part
    zs += [z0 + (z1 - z0) * j / 8.0 for j in range(9)]
    levels = merge_levels(zs, Z_SEAM + SEAM_GAP * 0.5, Z_TOP)

    loops = []
    for z in levels:
        a, b = shell_half_sizes(z)
        ix_top = arc_inset(z - (Z_TOP - R_TOP_X), R_TOP_X)
        loop = []
        for (px, py) in rr2d(a, b, R_VERT, m=12, k=10):
            a_here = a + ix_top * (1.0 - top_round_gain(py))
            loop.append(Bd.v(px * (a_here / a), py, z))
        loops.append(loop)
    loft(Bd, loops, MAT_WHITE)
    cap(Bd, loops[0], (0.0, 0.0, levels[0]), MAT_DARK, rings=5)     # hidden in the seam
    cap(Bd, loops[-1], (0.0, 0.0, levels[-1]), MAT_WHITE, rings=6)  # top face


def add_plinth(Bd):
    a_t, b_t = shell_half_sizes(Z_SEAM)
    a_t -= 0.0015
    b_t -= 0.0015
    z_top = Z_SEAM - SEAM_GAP * 0.5
    levels = merge_levels(
        [Z_BOT + BASE_FILLET * math.sin(0.5 * math.pi * j / 8.0) for j in range(9)],
        Z_BOT, z_top)
    loops = []
    for z in levels:
        ins = arc_inset(Z_BOT + BASE_FILLET - z, BASE_FILLET)
        loops.append([Bd.v(p[0], p[1], z) for p in rr2d(a_t - ins, b_t - ins, R_VERT, m=12, k=10)])
    loft(Bd, loops, MAT_WHITE)
    cap(Bd, loops[0], (0.0, 0.0, Z_BOT), MAT_WHITE, rings=5)   # underside
    cap(Bd, loops[-1], (0.0, 0.0, z_top), MAT_DARK, rings=4)   # hidden in the seam


# ------------------------------------------------------------------------------- ears
def add_ear(Bd, apex_x):
    """Front-view silhouette built from three tangent arcs, lofted as horizontal ellipses.
    X = outward distance from the centre line, z relative to the top surface."""
    TX = abs(apex_x)                       # apex distance from the centre line
    TZ, RHO = 0.0838, 0.0465               # rounded tip (centre height, radius)
    COX, COZ = TX - 0.2262, -0.0905        # centre of the convex outer flank arc
    CIX, CIZ = TX + 0.3363, -0.3060        # centre of the concave inner flank arc
    RO = math.hypot(TX - COX, TZ - COZ) + RHO
    RI = math.hypot(TX - CIX, TZ - CIZ) + RHO
    z_po = COZ + RO * (TZ - COZ) / math.hypot(TX - COX, TZ - COZ)   # outer flank -> tip
    z_pi = CIZ + RI * (TZ - CIZ) / math.hypot(TX - CIX, TZ - CIZ)   # inner flank -> tip

    def cap_half(z):
        return math.sqrt(max(RHO * RHO - (z - TZ) ** 2, 0.0))

    def x_out(z):
        # outer boundary: convex flank arc, then the outer branch of the tip cap
        if z <= z_po:
            return COX + math.sqrt(max(RO * RO - (z - COZ) ** 2, 0.0))
        return TX + cap_half(z)

    def x_in(z):
        # inner boundary: concave flank arc, then the inner branch of the tip cap
        if z <= z_pi:
            return CIX - math.sqrt(max(RI * RI - (z - CIZ) ** 2, 0.0))
        return TX - cap_half(z)

    def tuck(z):
        # pull the buried lower flank slightly inwards so it stays inside the shoulder
        return 0.004 * smooth((-0.095 - z) / 0.03)

    z_base = -0.13
    a0 = math.asin((z_base - COZ) / RO)
    a1 = math.asin((z_po - COZ) / RO)
    zs = [COZ + RO * math.sin(a0 + (a1 - a0) * j / 44.0) for j in range(45)]
    b1 = math.asin((z_po - TZ) / RHO)
    zs += [TZ + RHO * math.sin(b1 + (0.495 * math.pi - b1) * j / 12.0) for j in range(1, 13)]

    sign = -1.0 if apex_x < 0.0 else 1.0
    n = 48
    ang = [2.0 * math.pi * i / n for i in range(n)]
    loops = []
    for z in zs:
        xo = x_out(z) - tuck(z)
        xi = x_in(z)
        c = 0.5 * (xo + xi)
        rx = max(0.5 * (xo - xi), 0.0012)
        ry = EAR_DEPTH * rx
        loops.append([Bd.v(sign * (c + rx * math.cos(t)), EAR_Y + ry * math.sin(t), Z_TOP + z)
                      for t in ang])
    loft(Bd, loops, MAT_WHITE)
    c_base = 0.5 * (x_out(z_base) - tuck(z_base) + x_in(z_base))
    cap(Bd, loops[0], (sign * c_base, EAR_Y, Z_TOP + z_base), MAT_WHITE, rings=3)
    tip = Bd.v(sign * TX, EAR_Y, Z_TOP + TZ + RHO)
    last = loops[-1]
    for j in range(n):
        Bd.f((last[j], last[j + 1 if j + 1 < n else 0], tip), MAT_WHITE)


# ----------------------------------------------------------------------- top controls
def add_puck(Bd, cx, cy, rad, h, fillet, mat, n=64):
    """Low round button: cylinder with a rounded top edge, buried 0.045 in the body."""
    z0 = Z_TOP
    prof = [(0.0, z0 - 0.045), (rad, z0 - 0.045), (rad, z0 + h - fillet)]
    for j in range(1, 9):
        t = 0.5 * math.pi * j / 8.0
        prof.append((rad - fillet + fillet * math.cos(t), z0 + h - fillet + fillet * math.sin(t)))
    prof.append((0.0, z0 + h))
    lathe(Bd, prof, n, mat, cx, cy)


def add_knob(Bd, cx, cy):
    R, H, CH = KNOB_R, KNOB_H, KNOB_CHAMFER
    n = KNOB_FLUTES * 6
    ang = [2.0 * math.pi * i / n for i in range(n)]

    def ring(rad, amp, z):
        pts = []
        for t in ang:
            rr = rad - KNOB_DEPTH * amp * (1.0 - math.cos(KNOB_FLUTES * t)) * 0.5
            pts.append(Bd.v(cx + rr * math.cos(t), cy + rr * math.sin(t), z))
        return pts

    z0 = Z_TOP
    # recessed dark collar: reads as the shadow gap under the knob
    lathe(Bd, [(0.0, z0 - 0.020), (R - 0.006, z0 - 0.020), (R - 0.006, z0 + 0.0035),
               (0.0, z0 + 0.0035)], 64, MAT_DARK, cx, cy)
    rings = [ring(R - 0.0025, 0.0, z0 + 0.0025),
             ring(R, 0.4, z0 + 0.0055),
             ring(R, 1.0, z0 + 0.0100),
             ring(R, 1.0, z0 + H - CH - 0.003),
             ring(R, 0.3, z0 + H - CH),
             ring(R - CH, 0.0, z0 + H)]
    loft(Bd, rings, MAT_STEEL)
    cap(Bd, rings[-1], (cx, cy, z0 + H), MAT_KNOBTOP, rings=4)
    cap(Bd, rings[0], (cx, cy, z0 + 0.0025), MAT_DARK, rings=1)


# ------------------------------------------------------------------------------ feet
def add_foot(Bd, cx, cy):
    r, h, f = FOOT_R, ZB, 0.004
    prof = [(0.0, 0.0), (r - f, 0.0)]
    for j in range(1, 5):
        t = 0.5 * math.pi * j / 4.0
        prof.append((r - f + f * math.sin(t), f - f * math.cos(t)))
    prof += [(r, h + 0.012), (0.0, h + 0.012)]
    lathe(Bd, prof, 48, MAT_DARK, cx, cy)


# ---------------------------------------------------------------------------- display
def add_display(Bd):
    """Black glass panel sitting slightly proud of the front face: dark hairline rim, a shallow
    grey bevel just inside the rim, then the flat glass.  Returns the glass depth (y)."""
    y_face = -HALF_D
    y_rim = y_face - 0.0070        # glass rim
    y_glass = y_face - 0.0030      # flat glass area (kept clear of the body: no z-fighting)
    y_hair = y_face - 0.0066       # top of the hairline ring
    y_back = y_face + 0.012        # buried in the body

    def mk(a, b, r, y, cz=DISP_CZ):
        return [Bd.v(p[0], y, cz + p[1]) for p in rr2d(a, b, r, m=18, k=16)]

    H_back = mk(DISP_A + DISP_HAIRLINE, DISP_B + DISP_HAIRLINE, DISP_R + DISP_HAIRLINE, y_back)
    H_top = mk(DISP_A + DISP_HAIRLINE, DISP_B + DISP_HAIRLINE, DISP_R + DISP_HAIRLINE, y_hair)
    G_rim = mk(DISP_A, DISP_B, DISP_R, y_rim)
    G_bev = mk(DISP_A - DISP_BEVEL, DISP_B - DISP_BEVEL - 0.004, DISP_R - DISP_BEVEL - 0.002,
               y_glass, DISP_CZ + 0.002)        # band is wider along the bottom edge

    loft(Bd, [H_back, H_top], MAT_BEZEL)        # rim wall
    loft(Bd, [H_top, G_rim], MAT_BEZEL)         # hairline ring
    loft(Bd, [G_rim, G_bev], MAT_BEVEL)         # shallow bevel band around the glass
    cap(Bd, G_bev, (0.0, y_glass, DISP_CZ + 0.002), MAT_SCREEN, rings=7)
    cap(Bd, H_back, (0.0, y_back, DISP_CZ), MAT_BEZEL, rings=1)
    return y_glass


# ------------------------------------------------------------------- pixel face art
# Rectangles measured on the reference in pixels: (x0, x1, y0, y1).
EYE = [(1548, 1631, 1020, 1050),        # top cap
       (1511, 1669, 1050, 1083),
       (1477, 1702, 1083, 1138),
       (1448, 1519, 1138, 1273),        # left wall of the "0"
       (1586, 1731, 1138, 1273),        # right wall (two cells wide)
       (1477, 1702, 1273, 1338),
       (1511, 1669, 1338, 1369),
       (1548, 1631, 1369, 1397)]        # bottom cap
EYE_SHIFT = 660                         # the right eye is the left eye translated, not mirrored
CREAM_SINGLE = [(2036, 2106, 810, 878)]                 # bright square above the nose
MOUTH = [(1942, 1971, 1343, 1370),                      # stair-stepped diagonal stroke
         (1908, 1951, 1370, 1398),
         (1908, 1943, 1396, 1402),
         (1878, 1929, 1400, 1410),
         (1878, 1912, 1409, 1430)]
BLUSH_L = [(1374, 1414, 1369, 1417), (1443, 1476, 1399, 1432)]   # big + trailing small square
BLUSH_R = [(2387, 2425, 1369, 1417), (2446, 2478, 1399, 1431)]
GREY_SINGLE = [(1770, 1838, 844, 910), (1905, 1972, 844, 910)]  # two dim squares


def add_slab(Bd, x0, x1, z0, z1, y_front, thick, mat):
    """Thin emissive tile lying on the glass (a closed box, front face toward -Y)."""
    yb = y_front + thick
    p = [(x, y, z) for y in (y_front, yb) for z in (z0, z1) for x in (x0, x1)]
    a, b, c, d, e, f, g, h = [Bd.v(*co) for co in p]   # front: a b c d   back: e f g h
    for quad in ((a, b, d, c),      # front (-Y)
                 (e, f, h, g),      # back
                 (a, b, f, e),      # bottom
                 (c, d, h, g),      # top
                 (a, c, g, e),      # left
                 (b, d, h, f)):     # right
        Bd.f(quad, mat)


def add_slot(Bd, cx, cy, hx, hy, mat):
    """Tiny dark slot flush with the top face."""
    z0, z1 = Z_TOP - 0.004, Z_TOP + 0.0004
    p = [(x, y, z) for z in (z0, z1) for y in (cy - hy, cy + hy) for x in (cx - hx, cx + hx)]
    a, b, c, d, e, f, g, h = [Bd.v(*co) for co in p]   # bottom: a b c d   top: e f g h
    for quad in ((e, f, h, g), (a, b, d, c), (a, b, f, e), (c, d, h, g), (a, c, g, e), (b, d, h, f)):
        Bd.f(quad, mat)


def add_face(Bd, y_glass):
    yf = y_glass - 0.0020
    right_eye = [(x0 + EYE_SHIFT, x1 + EYE_SHIFT, y0, y1) for (x0, x1, y0, y1) in EYE]
    tiles = [(MAT_CREAM, EYE + right_eye + CREAM_SINGLE + MOUTH + BLUSH_L + BLUSH_R),
             (MAT_GRAY, GREY_SINGLE)]
    for mat, rects in tiles:
        for (x0, x1, y0, y1) in rects:
            add_slab(Bd, ux(x0), ux(x1), uz(y1), uz(y0), yf, 0.0030, mat)


# ------------------------------------------------------------------------------ build
def finalize(Bd, materials):
    bm = Bd.bm
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    for e in bm.edges:                      # creases sharper than SHARP_ANGLE stay crisp
        lf = e.link_faces
        if len(lf) == 2 and lf[0].normal.angle(lf[1].normal, 0.0) > SHARP_ANGLE:
            e.smooth = False
    me = bpy.data.meshes.new(OBJ_NAME + "Mesh")
    bm.to_mesh(me)
    bm.free()
    for m in materials:
        me.materials.append(m)
    fixed = me.validate(verbose=False)
    me.update()
    ob = bpy.data.objects.new(OBJ_NAME, me)
    try:
        coll = bpy.context.collection          # keep the file's own collection layout
    except Exception:
        coll = None
    (coll or bpy.context.scene.collection).objects.link(ob)
    try:
        bpy.context.view_layer.update()
        for other in bpy.context.view_layer.objects:
            if other is not None and other is not ob:
                other.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
    except Exception:
        pass
    return ob, fixed


def main():
    reset_scene()
    materials = build_materials()

    Bd = Builder()
    add_shell(Bd)
    add_plinth(Bd)
    for apex_x in EAR_APEX_X:
        add_ear(Bd, apex_x)
    for (cx, cy) in BUTTONS:
        add_puck(Bd, cx, cy, BUTTON_R, BUTTON_H, BUTTON_FILLET, MAT_WHITE)
    add_puck(Bd, LED[0], LED[1], 0.0125, 0.006, 0.0025, MAT_LED, n=32)
    for (mx, my) in MARKS:
        add_slot(Bd, mx, my, 0.0090, 0.0030, MAT_BEZEL)
    add_knob(Bd, KNOB[0], KNOB[1])
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            add_foot(Bd, sx * FOOT_X, sy * FOOT_Y)
    y_glass = add_display(Bd)
    add_face(Bd, y_glass)

    ob, fixed = finalize(Bd, materials)
    me = ob.data
    print("[catrobot] object=%s verts=%d faces=%d materials=%d validate_fixed=%s" % (
        ob.name, len(me.vertices), len(me.polygons), len(me.materials), fixed))
    print("[catrobot] bounds x[%.3f, %.3f] y[%.3f, %.3f] z[%.3f, %.3f]" % (
        min(v.co.x for v in me.vertices), max(v.co.x for v in me.vertices),
        min(v.co.y for v in me.vertices), max(v.co.y for v in me.vertices),
        min(v.co.z for v in me.vertices), max(v.co.z for v in me.vertices)))


main()
