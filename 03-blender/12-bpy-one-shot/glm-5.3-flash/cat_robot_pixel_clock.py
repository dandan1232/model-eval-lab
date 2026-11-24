# Cat-robot pixel alarm clock — one-shot procedural reconstruction for Blender 5.0
#
# Reference image observations (single 4K 3/4-front product shot, encoded here because
# the images are unavailable at runtime):
#   * A white, heavily rounded box body (a cat head), wider than tall, wider than deep.
#     Rough proportions W:H:D ~ 1.0 : 0.76 : 0.75. Soft pillow-like edges (large radius).
#   * Two smooth white cat ears (curved tapered horns, elliptical cross-section) on the
#     top corners, leaning outward ~12-15 deg, tips rounded, bases embedded in the top.
#   * On the top face, slightly toward the front: three small white cylindrical buttons
#     (flat tops, tiny chamfer) clustered left of center, and one larger brushed-metal
#     knurled rotary knob on the right, partially tucked in front of the right ear.
#     A tiny dark dot (mic / LED) sits left of the first button.
#   * Front face: a large glossy black rounded-rectangle display slab standing slightly
#     proud of the white body (~2/3 of the front), warm-white LED pixel art on it:
#     - two big round pixel eyes (5x6 blobs) with dark 1x2 rectangular pupils,
#     - two gray squares + one bright white square above (diagonal, like a status mark),
#     - three pairs of small cream pixels below (cheeks / tiny pixel mouth squiggle).
#   * A parting seam near the bottom: a slightly inset rounded skirt section, and two
#     (plus two mirrored rear) small dark rubber feet under it.
#   * Materials: matte warm-white plastic (body/ears/buttons), glossy black glass
#     (display), emissive warm-cream pixels, brushed aluminum knob, dark matte feet.

import bpy
import bmesh
import math
from mathutils import Matrix

# ------------------------------------------------------------------
# Clear the default scene (cube, camera, light...)
# ------------------------------------------------------------------
for _ob in list(bpy.data.objects):
    bpy.data.objects.remove(_ob, do_unlink=True)


# ------------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------------
def _link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _bm_to_obj(name, bm, mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.validate(verbose=0)
    obj = bpy.data.objects.new(name, me)
    if mat is not None:
        me.materials.append(mat)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    return _link(obj)


def rounded_box(name, dims, bevel, segments, loc, mat):
    """A box with all edges heavily beveled (pill/rounded-cube look)."""
    bm = bmesh.new()
    mtx = Matrix.Translation(loc) @ Matrix.Diagonal((dims[0], dims[1], dims[2], 1.0))
    bmesh.ops.create_cube(bm, size=1.0, matrix=mtx)
    bmesh.ops.bevel(bm, geom=list(bm.edges), offset=bevel, segments=segments,
                    profile=0.5, affect='EDGES', clamp_overlap=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _bm_to_obj(name, bm, mat)


def cone_part(name, r1, r2, depth, segments, loc, mat,
              bevel_top=0.0, bevel_bot=0.0):
    """Cylinder/cone with optional chamfers on its cap rims."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=r1, radius2=r2, depth=depth,
                          matrix=Matrix.Translation(loc))
    cx, cy = loc[0], loc[1]
    zt, zb = loc[2] + depth / 2.0, loc[2] - depth / 2.0
    rmin = 0.5 * max(r1, r2)

    def rim(zc):
        return [e for e in bm.edges
                if all(abs(v.co.z - zc) < 1e-4 for v in e.verts)
                and all(math.hypot(v.co.x - cx, v.co.y - cy) > rmin for v in e.verts)]

    for zc, off in ((zt, bevel_top), (zb, bevel_bot)):
        if off > 1e-6:
            es = rim(zc)
            if es:
                try:
                    bmesh.ops.bevel(bm, geom=es, offset=off, segments=3,
                                    profile=0.6, affect='EDGES', clamp_overlap=True)
                except Exception:
                    pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _bm_to_obj(name, bm, mat)


def rounded_rect_pts(w, h, r, seg):
    """Closed rounded-rectangle outline in the XZ plane, centered on origin."""
    pts = []
    corners = [(w / 2 - r, h / 2 - r, 0.0),
               (-w / 2 + r, h / 2 - r, math.pi / 2),
               (-w / 2 + r, -h / 2 + r, math.pi),
               (w / 2 - r, -h / 2 + r, 1.5 * math.pi)]
    for cx, cz, a0 in corners:
        for i in range(seg):
            a = a0 + (math.pi / 2) * i / seg
            pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    return pts


# ------------------------------------------------------------------
# Materials
# ------------------------------------------------------------------
def mat_plastic(name, rgb, rough, metallic=0.0, coat=0.0, spec=0.4, aniso=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    # Look up by node type id (node *names* can be locale-translated)
    bsdf = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
    if bsdf is None:
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')

    def seti(nm, v):
        s = bsdf.inputs.get(nm)
        if s is not None:
            s.default_value = v

    seti('Base Color', (*rgb, 1.0))
    seti('Roughness', rough)
    seti('Metallic', metallic)
    seti('Specular IOR Level', spec)
    seti('Coat Weight', coat)
    seti('Anisotropic', aniso)
    return m


def mat_emit(name, rgb, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*rgb, 1.0)
    em.inputs['Strength'].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m


mat_body = mat_plastic('body_plastic', (0.93, 0.92, 0.89), 0.35, coat=0.05)
mat_screen = mat_plastic('screen_glass', (0.010, 0.010, 0.012), 0.15, coat=0.25, spec=0.5)
mat_metal = mat_plastic('knob_alu', (0.78, 0.78, 0.80), 0.32, metallic=1.0, aniso=0.5)
mat_dark = mat_plastic('dark_parts', (0.02, 0.02, 0.02), 0.55, spec=0.3)
mat_px_cream = mat_emit('px_cream', (1.0, 0.93, 0.80), 3.2)
mat_px_white = mat_emit('px_white', (1.0, 0.99, 0.94), 7.0)
mat_px_gray = mat_emit('px_gray', (0.42, 0.42, 0.42), 1.0)

# ------------------------------------------------------------------
# Body, bottom skirt, feet
# ------------------------------------------------------------------
rounded_box('body', (1.0, 0.75, 0.755), 0.13, 14, (0.0, 0.0, 0.4525), mat_body)
rounded_box('skirt', (0.955, 0.70, 0.055), 0.022, 8, (0.0, 0.0, 0.0525), mat_body)
for sx in (-1, 1):
    for sy in (-1, 1):
        rounded_box('foot_%d%d' % (sx, sy), (0.15, 0.11, 0.06), 0.02, 3,
                    (0.30 * sx, 0.27 * sy, 0.03), mat_dark)

# ------------------------------------------------------------------
# Display slab: glossy black rounded rectangle standing proud of the front
# ------------------------------------------------------------------
SLAB_W, SLAB_H, SLAB_R = 0.74, 0.585, 0.075
SLAB_CZ = 0.4525
SLAB_YBACK, SLAB_DEPTH = -0.352, 0.035  # front face at y = -0.387


def build_slab():
    bm = bmesh.new()
    pts = rounded_rect_pts(SLAB_W, SLAB_H, SLAB_R, 12)
    yb, yf = SLAB_YBACK, SLAB_YBACK - SLAB_DEPTH
    fv = [bm.verts.new((x, yf, z + SLAB_CZ)) for x, z in pts]
    bv = [bm.verts.new((x, yb, z + SLAB_CZ)) for x, z in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((fv[i], fv[j], bv[j], bv[i]))
    bm.faces.new(list(reversed(fv)))
    bm.faces.new(bv)
    rim = [e for e in bm.edges if abs(e.verts[0].co.y - e.verts[1].co.y) < 1e-6]
    try:
        bmesh.ops.bevel(bm, geom=rim, offset=0.004, segments=2,
                        profile=0.7, affect='EDGES', clamp_overlap=True)
    except Exception:
        pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _bm_to_obj('display', bm, mat_screen)


build_slab()

# ------------------------------------------------------------------
# Ears: two tapered elliptical horns leaning outward, rounded tips
# ------------------------------------------------------------------
def build_ear(name, sign):
    bm = bmesh.new()
    n_th = 24
    bx, by, bz, H = sign * 0.33, 0.10, 0.68, 0.30
    rx0, ry0, lean = 0.095, 0.072, 0.10
    prof = [0.0, 0.10, 0.22, 0.34, 0.46, 0.58, 0.70, 0.80, 0.88, 0.94, 0.985]

    def taper(u):
        if u <= 0.80:
            return 1.0 - 0.62 * (u / 0.80)
        return 0.38 * math.sqrt(max(0.0, 1.0 - ((u - 0.80) / 0.20) ** 2))

    rings = []
    for u in prof:
        z = bz + H * u
        cx = bx + sign * lean * (u ** 1.4)
        cy = by + 0.02 * u
        t = taper(u)
        ring = []
        for k in range(n_th):
            a = 2 * math.pi * k / n_th
            ring.append(bm.verts.new((cx + t * rx0 * math.cos(a),
                                      cy + t * ry0 * math.sin(a), z)))
        rings.append(ring)
    for i in range(len(rings) - 1):
        ra, rb = rings[i], rings[i + 1]
        for k in range(n_th):
            k2 = (k + 1) % n_th
            bm.faces.new((ra[k], ra[k2], rb[k2], rb[k]))
    bm.faces.new(list(reversed(rings[0])))
    apex = bm.verts.new((bx + sign * lean, by + 0.02, bz + H))
    top = rings[-1]
    for k in range(n_th):
        k2 = (k + 1) % n_th
        bm.faces.new((top[k], top[k2], apex))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return _bm_to_obj(name, bm, mat_body)


build_ear('ear_L', -1)
build_ear('ear_R', 1)

# ------------------------------------------------------------------
# Top controls: three white buttons, tiny dark dot, knurled metal knob
# ------------------------------------------------------------------
BTN_Y = -0.02
for i, bx in enumerate((-0.23, -0.115, 0.015)):
    cone_part('button_%d' % i, 0.042, 0.042, 0.075, 32,
              (bx, BTN_Y, 0.8225), mat_body, bevel_top=0.009)
cone_part('mic_dot', 0.013, 0.013, 0.02, 16,
          (-0.31, BTN_Y, 0.825), mat_dark)

KNB_X, KNB_Y, KNB_R = 0.30, -0.02, 0.105
knob = cone_part('knob', KNB_R, KNB_R, 0.105, 126,
                 (KNB_X, KNB_Y, 0.8425), mat_metal, bevel_top=0.008)
# Flute the knob: 42 fine vertical knurl ridges via radial modulation
me = knob.data
for v in me.vertices:
    dx, dy = v.co.x - KNB_X, v.co.y - KNB_Y
    r = math.hypot(dx, dy)
    if r > 1e-4:
        s = 1.0 + (0.0075 / KNB_R) * math.cos(42 * math.atan2(dy, dx))
        v.co.x = KNB_X + dx * s
        v.co.y = KNB_Y + dy * s

# ------------------------------------------------------------------
# Pixel-art face: 16 x 12 LED grid on the display
# ------------------------------------------------------------------
P = 0.0375                  # pixel pitch
GX0, GZ0 = -0.30, 0.2275    # grid origin (lower-left cell corner)
PY = -0.390                 # pixel box center depth (protrudes ~7 mm)
PDEPTH = 0.008

cream, gray, white = set(), {(7, 10), (8, 10)}, {(9, 11)}
pupils = {(3, 5), (3, 6), (12, 5), (12, 6)}

# Eyes: rounded-rectangle pixel ovals, 4 wide x 6 tall, 2-wide caps top/bottom
for base_col in (2, 10):           # cols base..base+3, rows 3..8
    cream.add((base_col + 1, 8)), cream.add((base_col + 2, 8))
    for c in range(base_col, base_col + 4):
        for r in (7, 6, 5, 4):
            cream.add((c, r))
    cream.add((base_col + 1, 3)), cream.add((base_col + 2, 3))
cream -= pupils
cream |= {(2, 2), (3, 1), (13, 2), (12, 1), (8, 1), (9, 2)}  # cheeks + tiny mouth tick


def pixel_boxes(name, cells, mat):
    bm = bmesh.new()
    for (c, r) in cells:
        x = GX0 + (c + 0.5) * P
        z = GZ0 + (r + 0.5) * P
        tmp = bmesh.ops.create_cube(bm, size=1.0)
        for v in tmp['verts']:
            v.co.x = x + v.co.x * P * 0.92
            v.co.y = PY + v.co.y * PDEPTH
            v.co.z = z + v.co.z * P * 0.92
    return _bm_to_obj(name, bm, mat, smooth=False)


pixel_boxes('pixels_cream', cream, mat_px_cream)
pixel_boxes('pixels_gray', gray, mat_px_gray)
pixel_boxes('pixels_white', white, mat_px_white)

print('cat-robot pixel clock built: %d objects' % len(bpy.data.objects))
