"""Builds the 3D shop set in Blender (Cycles) and renders frames.

Run with the bpy venv:  python src/scene.py --frames 0-395 [--res 0.8] [--samples 40] [--out build/frames3d]
No people appear anywhere. All models and textures are CC0 (Poly Haven).
"""
import bpy, bmesh, math, os, sys, glob, json, argparse, addon_utils
from mathutils import Vector, Euler

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
P = lambda *a: os.path.join(ROOT, *a)
sys.path.insert(0, os.path.dirname(__file__))
from timing import *

TEAL = (0.0060, 0.1144, 0.1301)        # 115E67 in linear
WARM = (0.930, 0.913, 0.871)            # F7F5F0
APRICOT = (0.888, 0.468, 0.159)         # F2B66D
srgb = lambda h: tuple(((int(h[i:i + 2], 16) / 255 + 0.055) / 1.055) ** 2.4 for i in (0, 2, 4))


# ---------------------------------------------------------------- helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    addon_utils.enable('cycles')


def link(o):
    bpy.context.scene.collection.objects.link(o); return o


def box(name, size, loc, mat=None, bevel=0.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts: v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.location = loc
    if mat: me.materials.append(mat)
    if bevel:
        m = o.modifiers.new('bev', 'BEVEL'); m.width = bevel; m.segments = 3; m.limit_method = 'ANGLE'
        for p in me.polygons: p.use_smooth = True
        mm = o.modifiers.new('wn', 'WEIGHTED_NORMAL')
    return o


def plane(name, w, h, loc, rot=(0, 0, 0), mat=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5)
    for v in bm.verts: v.co = Vector((v.co.x * w, v.co.y * h, 0))
    uv = bm.loops.layers.uv.new()
    for f in bm.faces:
        for l in f.loops: l[uv].uv = (l.vert.co.x / w + 0.5, l.vert.co.y / h + 0.5)
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); o.location = loc; o.rotation_euler = rot
    if mat: me.materials.append(mat)
    return o


def node_mat(name):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    return m, nt, out


def pbr(name, tex, scale=1.0, tint=None, rough=None, rough_mul=1.0, bump=1.0, box_blend=0.25, spec=0.5):
    m, nt, out = node_mat(name)
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(bs.outputs[0], out.inputs[0])
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / scale,) * 3
    nt.links.new(tc.outputs['Object'], mp.inputs[0])
    d = P('assets/tex', tex)
    def img(fn, col):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(d, fn), check_existing=True)
        t.image.colorspace_settings.name = 'sRGB' if col else 'Non-Color'
        t.projection = 'BOX'; t.projection_blend = box_blend
        nt.links.new(mp.outputs[0], t.inputs[0]); return t
    dif = img('diff.jpg', True)
    if tint:
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        nt.links.new(dif.outputs[0], mix.inputs['A']); mix.inputs['B'].default_value = (*tint, 1)
        nt.links.new(mix.outputs['Result'], bs.inputs['Base Color'])
    else:
        nt.links.new(dif.outputs[0], bs.inputs['Base Color'])
    if rough is None:
        r = img('rough.jpg', False)
        mt = nt.nodes.new('ShaderNodeMath'); mt.operation = 'MULTIPLY'; mt.inputs[1].default_value = rough_mul
        nt.links.new(r.outputs[0], mt.inputs[0]); nt.links.new(mt.outputs[0], bs.inputs['Roughness'])
    else:
        bs.inputs['Roughness'].default_value = rough
    n = img('nor.jpg', False); nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = bump
    nt.links.new(n.outputs[0], nm.inputs['Color']); nt.links.new(nm.outputs[0], bs.inputs['Normal'])
    bs.inputs['Specular IOR Level'].default_value = spec
    return m


def simple(name, color, rough=0.5, metal=0.0, emit=None, emit_strength=0.0):
    m, nt, out = node_mat(name)
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); nt.links.new(bs.outputs[0], out.inputs[0])
    bs.inputs['Base Color'].default_value = (*color, 1); bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    if emit:
        bs.inputs['Emission Color'].default_value = (*emit, 1); bs.inputs['Emission Strength'].default_value = emit_strength
    return m


def glass_mat(name='glass'):
    """Architectural glass: lets sunlight through (no caustic blocking), reflects at grazing angles."""
    m, nt, out = node_mat(name)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); tr.inputs[0].default_value = (0.93, 0.97, 0.96, 1)
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.02
    fr = nt.nodes.new('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.5
    mx = nt.nodes.new('ShaderNodeMixShader')
    ad = nt.nodes.new('ShaderNodeMath'); ad.operation = 'ADD'; ad.inputs[1].default_value = 0.06
    nt.links.new(fr.outputs[0], ad.inputs[0]); nt.links.new(ad.outputs[0], mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
    return m


def screen_mat(name, seq_dir, prefix, start, count, strength=1.0):
    """Emissive screen with a glass reflection layer, driven by an image sequence."""
    m, nt, out = node_mat(name)
    t = nt.nodes.new('ShaderNodeTexImage')
    first = os.path.join(seq_dir, '%s%04d.png' % (prefix, 0))
    im = bpy.data.images.load(first); im.source = 'SEQUENCE'; t.image = im
    t.image_user.frame_duration = count; t.image_user.frame_start = 0; t.image_user.frame_offset = 0
    t.image_user.use_auto_refresh = True; t.interpolation = 'Cubic'
    uv = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(uv.outputs['UV'], t.inputs[0])
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = strength
    nt.links.new(t.outputs[0], em.inputs[0])
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.05
    fr = nt.nodes.new('ShaderNodeLayerWeight'); fr.inputs['Blend'].default_value = 0.12
    ad = nt.nodes.new('ShaderNodeAddShader'); mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(fr.outputs['Fresnel'], mx.inputs[0]); nt.links.new(em.outputs[0], mx.inputs[1]); nt.links.new(gl.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return m


def import_model(name, loc, rot=(0, 0, 0), scale=1.0, skip=()):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=glob.glob(P('assets/models', name, '*.gltf'))[0])
    new = [o for o in bpy.data.objects if o not in before]
    root = bpy.data.objects.new(name + '_root', None); link(root)
    for o in new:
        if any(s in o.name for s in skip): bpy.data.objects.remove(o); continue
        if o.parent is None: o.parent = root
    root.location = loc; root.rotation_euler = rot; root.scale = (scale,) * 3
    return root


def fcurves_of(idb):
    ad = getattr(idb, 'animation_data', None)
    if not ad or not ad.action: return []
    act = ad.action
    if hasattr(act, 'layers') and len(act.layers):
        out = []
        for L in act.layers:
            for st in L.strips:
                for cb in st.channelbags: out += list(cb.fcurves)
        return out
    return list(getattr(act, 'fcurves', []))


def set_interp(idb, interp, easing=None):
    for fc in fcurves_of(idb):
        for kp in fc.keyframe_points:
            kp.interpolation = interp
            if easing: kp.easing = easing


def look_at(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def key(obj, path, frame, value, interp='BEZIER'):
    setattr(obj, path, value) if not isinstance(path, tuple) else None
    obj.keyframe_insert(data_path=path, frame=frame)


# ---------------------------------------------------------------- set
def build():
    reset()
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    sc.render.fps = FPS
    sc.view_settings.view_transform = 'AgX'; sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.cycles.max_bounces = 5; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False; sc.cycles.blur_glossy = 1.0
    sc.cycles.transmission_bounces = 4; sc.cycles.transparent_max_bounces = 8
    sc.cycles.sample_clamp_indirect = 8; sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.render.use_persistent_data = True

    # world: Bryanston (Johannesburg) sunrise HDRI
    w = bpy.data.worlds.new('world'); sc.world = w; w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    o = nt.nodes.new('ShaderNodeOutputWorld'); bg = nt.nodes.new('ShaderNodeBackground')
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(P('assets/hdri/bryanston_park_sunrise_4k.hdr'))
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, math.radians(200))
    nt.links.new(tc.outputs['Generated'], mp.inputs[0]); nt.links.new(mp.outputs[0], env.inputs[0])
    nt.links.new(env.outputs[0], bg.inputs[0]); bg.inputs[1].default_value = 0.9; nt.links.new(bg.outputs[0], o.inputs[0])

    # low warm sun raking from the left
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 4.2; sun.angle = math.radians(0.8)
    sun.color = (1.0, 0.78, 0.55)
    so = link(bpy.data.objects.new('sun', sun)); so.rotation_euler = Euler((math.radians(77), 0, math.radians(-52)))

    M = dict(
        brick=pbr('brick', 'whitewashed_brick', 1.4, tint=(0.95, 0.93, 0.9)),
        plaster=pbr('plaster', 'white_plaster_02', 1.5, tint=(0.93, 0.91, 0.87), bump=0.4),
        teal=pbr('tealwall', 'white_plaster_02', 1.5, tint=tuple(c * 1.6 for c in TEAL), bump=0.5),
        tiles=pbr('tiles', 'long_white_tiles', 0.9, rough_mul=0.6, spec=0.6),
        floor=pbr('floor', 'terrazzo_tiles', 1.2, rough_mul=0.7),
        pave=pbr('pave', 'concrete_floor_worn_001', 2.0),
        road=pbr('road', 'asphalt_02', 3.0),
        oak=pbr('oak', 'white_oak_veneer', 0.9, rough_mul=0.8),
        planks=pbr('planks', 'white_planks_clean', 1.0, tint=tuple(c * 1.9 for c in TEAL)),
        frame=simple('alu_dark', (0.03, 0.035, 0.04), 0.35, 1.0),
        alu=simple('alu', (0.75, 0.76, 0.78), 0.28, 1.0),
        black=simple('black', (0.01, 0.01, 0.012), 0.25),
        glass=glass_mat(),
        shutter_box=simple('shutter_box', (0.62, 0.63, 0.62), 0.45, 0.6),
        fascia=simple('fascia', WARM, 0.6),
        apricot=simple('apricot', APRICOT, 0.5),
    )

    # ---- street and facade (shop front at y = 0, street at y < 0)
    plane('road', 40, 30, (0, -19.3, 0), mat=M['road'])
    box('kerb', (40, 0.3, 0.15), (0, -4.15, 0.075), M['pave'])
    box('pavement', (40, 3.9, 0.15), (0, -2.2, 0.075), M['pave'])
    Z0 = 0.15  # pavement top
    for x0, x1 in ((-6, -1.65), (1.65, 6)):
        box('pier', (x1 - x0, 0.3, 4.4), ((x0 + x1) / 2, -0.15, Z0 + 2.2), M['brick'])
    box('lintel', (3.3, 0.3, 1.6), (0, -0.15, Z0 + 2.65 + 0.8), M['brick'])
    box('fascia', (12, 0.08, 0.7), (0, -0.34, Z0 + 3.45), M['fascia'])
    box('fascia_line', (12, 0.085, 0.05), (0, -0.345, Z0 + 3.12), M['apricot'])
    box('shutter_box', (3.4, 0.36, 0.34), (0, -0.48, Z0 + 2.82), M['shutter_box'], bevel=0.01)
    box('rail_l', (0.06, 0.1, 2.65), (-1.62, -0.36, Z0 + 1.325), M['shutter_box'])
    box('rail_r', (0.06, 0.1, 2.65), (1.62, -0.36, Z0 + 1.325), M['shutter_box'])

    # roller shutter curtain: real corrugations, slides up into the box; anything above the box is cut away in the shader
    me = bpy.data.meshes.new('curtain'); bm = bmesh.new()
    nx, nz = 2, 260; W_, H_ = 3.2, 2.65
    verts = [[bm.verts.new((-W_ / 2 + W_ * i / nx, -0.4 + 0.012 * math.sin(j / nz * H_ / 0.055 * 2 * math.pi), H_ * j / nz)) for j in range(nz + 1)] for i in range(nx + 1)]
    for i in range(nx):
        for j in range(nz): bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = True
    cur = link(bpy.data.objects.new('curtain', me)); cur.location = (0, 0, Z0)
    m, nt, out = node_mat('curtain')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); bs.inputs['Base Color'].default_value = (0.55, 0.57, 0.57, 1)
    bs.inputs['Metallic'].default_value = 0.7; bs.inputs['Roughness'].default_value = 0.42
    ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 6; ns.inputs['Detail'].default_value = 8
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (0.42, 0.43, 0.43, 1); cr.color_ramp.elements[1].color = (0.62, 0.64, 0.63, 1)
    nt.links.new(ns.outputs[0], cr.inputs[0]); nt.links.new(cr.outputs[0], bs.inputs['Base Color'])
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    gt = nt.nodes.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; gt.inputs[1].default_value = Z0 + 2.66
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(geo.outputs['Position'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], gt.inputs[0])
    nt.links.new(gt.outputs[0], mx.inputs[0]); nt.links.new(bs.outputs[0], mx.inputs[1]); nt.links.new(tr.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0]); me.materials.append(m)
    a, b = SHUTTER
    cur.location.z = Z0; cur.keyframe_insert('location', index=2, frame=a)
    cur.location.z = Z0 + H_ + 0.02; cur.keyframe_insert('location', index=2, frame=b)
    set_interp(cur, 'SINE', 'EASE_IN_OUT')

    # shopfront: glass in a dark aluminium frame, door on the right
    sf_y = 0.02
    box('kick', (3.24, 0.08, 0.32), (0, sf_y, Z0 + 0.16), M['frame'])
    box('head', (3.24, 0.08, 0.08), (0, sf_y, Z0 + 2.6), M['frame'])
    for x in (-1.6, -0.2, 0.62, 1.6): box('mullion', (0.07, 0.09, 2.5), (x, sf_y, Z0 + 1.32), M['frame'])
    plane('glass_l', 1.4, 2.25, (-0.9, sf_y, Z0 + 1.44), (math.radians(90), 0, 0), M['glass'])
    plane('glass_m', 0.82, 2.25, (0.21, sf_y, Z0 + 1.44), (math.radians(90), 0, 0), M['glass'])
    plane('glass_door', 0.9, 2.25, (1.11, sf_y, Z0 + 1.44), (math.radians(90), 0, 0), M['glass'])
    box('handle', (0.03, 0.06, 0.5), (0.72, sf_y + 0.06, Z0 + 1.1), simple('brass', (0.8, 0.55, 0.25), 0.25, 1.0))
    box('handle_o', (0.03, 0.06, 0.5), (0.72, sf_y - 0.06, Z0 + 1.1), simple('brass2', (0.8, 0.55, 0.25), 0.25, 1.0))

    # ---- interior (y 0.1 .. 5.6, x -3 .. 3, ceiling 3.2)
    box('floor_in', (6.4, 5.6, 0.04), (0, 2.85, Z0 - 0.0), M['floor'])
    box('back_wall', (6.4, 0.1, 3.4), (0, 5.65, Z0 + 1.7), M['tiles'])
    box('left_wall', (0.1, 5.6, 3.4), (-3.2, 2.85, Z0 + 1.7), M['teal'])
    box('right_wall', (0.1, 5.6, 3.4), (3.2, 2.85, Z0 + 1.7), M['plaster'])
    box('front_in_l', (1.55, 0.1, 3.4), (-2.43, 0.05, Z0 + 1.7), M['plaster'])
    box('front_in_r', (1.55, 0.1, 3.4), (2.43, 0.05, Z0 + 1.7), M['plaster'])
    box('front_in_top', (3.3, 0.1, 0.62), (0, 0.05, Z0 + 2.99), M['plaster'])
    box('ceiling', (6.4, 5.6, 0.06), (0, 2.85, Z0 + 3.3), M['plaster'])

    # counter
    CY, CH = 3.1, 0.95
    box('counter_body', (3.6, 0.62, CH - 0.04), (-0.3, CY, Z0 + (CH - 0.04) / 2), M['planks'])
    box('counter_top', (3.7, 0.7, 0.04), (-0.3, CY, Z0 + CH - 0.02), M['oak'], bevel=0.004)
    box('counter_kick', (3.6, 0.6, 0.08), (-0.3, CY + 0.02, Z0 + 0.04), M['black'])
    TOP = Z0 + CH
    # props on the counter
    import_model('wooden_cutting_board', (-1.55, CY - 0.05, TOP), (0, 0, 0.2))
    for i, (dx, dy, r) in enumerate(((-0.1, 0.02, 0.3), (0.05, -0.05, -0.4), (0.12, 0.06, 1.2))):
        import_model('croissant', (-1.55 + dx, CY - 0.05 + dy, TOP + 0.02), (0, 0, r))
    import_model('wicker_basket_01', (-0.95, CY + 0.05, TOP), (0, 0, 0.1))
    for dx, r in ((-0.06, 0.4), (0.07, -0.6)):
        import_model('croissant', (-0.95 + dx, CY + 0.05, TOP + 0.05), (0.15, 0, r))
    import_model('carrot_cake', (-0.35, CY + 0.1, TOP), (0, 0, 0.5))
    import_model('strawberry_chocolate_cake', (-2.0, CY + 0.12, TOP), (0, 0, 1.0))
    import_model('jug_01', (0.15, CY + 0.18, TOP), (0, 0, 2.6))
    import_model('ceramic_vase_02', (1.35, CY + 0.2, TOP), (0, 0, 0), 0.8)
    import_model('potted_plant_02', (-2.75, 1.0, Z0), (0, 0, 0.6), 1.3)
    # back wall shelves with a tea set
    for x in (-1.2, 0.3):
        import_model('wooden_display_shelves_01', (x, 5.4, Z0), (0, 0, math.radians(90)))
    import_model('tea_set_01', (-1.2, 5.38, Z0 + 1.56), (0, 0, 0), 0.9)
    import_model('ceramic_vase_02', (0.3, 5.4, Z0 + 1.56), (0, 0, 0), 0.9)
    # pendant lamps over the counter with bulbs that flicker on
    bulbs = []
    for x in (-1.6, -0.4, 0.8):
        import_model('hanging_industrial_lamp', (x, CY - 0.05, Z0 + 3.27), (0, 0, 0), 0.75)
        bl = bpy.data.lights.new('bulb', 'POINT'); bl.shadow_soft_size = 0.05; bl.color = (1.0, 0.78, 0.52)
        lo = link(bpy.data.objects.new('bulb', bl)); lo.location = (x, CY - 0.05, Z0 + 3.27 - 0.85)
        bulbs.append(bl)
    fill = bpy.data.lights.new('fill', 'AREA'); fill.size = 3.0; fill.color = (1.0, 0.86, 0.7)
    fo = link(bpy.data.objects.new('fill', fill)); fo.location = (0, 3.2, Z0 + 3.2); fo.rotation_euler = (0, 0, 0)
    # flicker: off until LIGHTS, a few stutters, then steady
    pattern = [(0, 0), (LIGHTS, 0), (LIGHTS + 1, 1), (LIGHTS + 2, 0.15), (LIGHTS + 4, 0.9), (LIGHTS + 5, 0.3), (LIGHTS + 7, 1.0), (395, 1.0)]
    for lt, full in [(b, 130.0) for b in bulbs] + [(fill, 650.0)]:
        for f, v in pattern:
            lt.energy = full * v; lt.keyframe_insert('energy', frame=f)
        set_interp(lt, 'CONSTANT')
    # visible glowing bulbs inside the shades
    bm_ = simple('bulb_glow', (1, 0.9, 0.7), 0.3, emit=(1.0, 0.8, 0.55), emit_strength=0.0)
    em_in = bm_.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    for f, v in pattern:
        em_in.default_value = 40 * v; em_in.keyframe_insert('default_value', frame=f)
    set_interp(bm_.node_tree, 'CONSTANT')
    for x in (-1.6, -0.4, 0.8):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.045, location=(x, CY - 0.05, Z0 + 3.27 - 0.88))
        bpy.context.object.data.materials.append(bm_)

    # ---- phone on the counter
    ph = box('phone', (0.0745, 0.1605, 0.0082), (0.55, CY - 0.14, TOP + 0.0041), simple('phone_body', (0.05, 0.06, 0.065), 0.3, 0.9), bevel=0.006)
    ph.rotation_euler = (0, 0, 0)
    scr = plane('phone_screen', 0.0695, 0.1503, (0, 0, 0.00415), mat=screen_mat('phone_screen', P('build/tex/phone'), 'p_', 0, S5[1], 1.6))
    scr.parent = ph
    # vibrate on BUZZ
    for i, f in enumerate(range(BUZZ - 2, BUZZ + 10)):
        j = 0 if f in (BUZZ - 2, BUZZ + 9) else (0.0016 if i % 2 else -0.0016)
        ph.location.x = 0.55 + j; ph.keyframe_insert('location', index=0, frame=f)
        ph.rotation_euler.z = math.radians((0.6 if i % 2 else -0.6) * (j != 0)); ph.keyframe_insert('rotation_euler', index=2, frame=f)

    # ---- laptop at the end of the counter
    lap = bpy.data.objects.new('laptop', None); link(lap); lap.location = (1.3, CY - 0.08, TOP); lap.rotation_euler = (0, 0, math.radians(16))
    base = box('lap_base', (0.304, 0.212, 0.012), (0, 0, 0.006), M['alu'], bevel=0.003); base.parent = lap
    kb = box('lap_keys', (0.27, 0.1, 0.0015), (0, 0.02, 0.0125), M['black']); kb.parent = lap
    hinge = bpy.data.objects.new('hinge', None); link(hinge); hinge.parent = lap; hinge.location = (0, 0.105, 0.012)
    hinge.rotation_euler = (math.radians(-12), 0, 0)
    lid = box('lap_lid', (0.304, 0.006, 0.212), (0, 0.003, 0.106), M['alu'], bevel=0.003); lid.parent = hinge
    bez = plane('lap_bezel', 0.296, 0.204, (0, -0.0006, 0.106), (math.radians(90), 0, 0), M['black']); bez.parent = hinge
    ls = plane('lap_screen', 0.282, 0.176, (0, -0.0009, 0.110), (math.radians(90), 0, 0),
               screen_mat('lap_screen', P('build/tex/laptop'), 'l_', 0, S5[1], 1.4)); ls.parent = hinge

    # ---- door sign on the inside of the door glass: Closed on one side, Open on the other
    sign = bpy.data.objects.new('sign', None); link(sign); sign.location = (1.11, sf_y + 0.05, Z0 + 1.62)
    def sign_face(img, rz, dy):
        m, nt, out = node_mat('sign_' + os.path.basename(img))
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(img)
        bs = nt.nodes.new('ShaderNodeBsdfPrincipled'); bs.inputs['Roughness'].default_value = 0.55
        nt.links.new(t.outputs[0], bs.inputs['Base Color']); nt.links.new(bs.outputs[0], out.inputs[0])
        nt.links.new(t.outputs[0], bs.inputs['Emission Color']); bs.inputs['Emission Strength'].default_value = 0.35
        f = plane('sign_face', 0.30, 0.15, (0, dy, 0), (math.radians(90), 0, rz), m); f.parent = sign
        return f
    sign_face(P('build/tex/sign_closed.png'), 0, -0.0022)    # faces the street (-y) before the flip
    sign_face(P('build/tex/sign_open.png'), math.radians(180), 0.0022)
    body = box('sign_body', (0.299, 0.003, 0.149), (0, 0, 0), simple('card', (0.85, 0.84, 0.8), 0.6)); body.parent = sign
    cord = box('cord', (0.004, 0.004, 0.12), (0, 0, 0.13), M['black']); cord.parent = sign
    a, b = FLIP
    sign.rotation_euler.z = 0; sign.keyframe_insert('rotation_euler', index=2, frame=a)
    sign.rotation_euler.z = math.radians(-180 - 14); sign.keyframe_insert('rotation_euler', index=2, frame=a + 9)
    sign.rotation_euler.z = math.radians(-180 + 6); sign.keyframe_insert('rotation_euler', index=2, frame=a + 14)
    sign.rotation_euler.z = math.radians(-180); sign.keyframe_insert('rotation_euler', index=2, frame=b)

    # ---- outside dressing
    import_model('jacaranda_tree', (-6.8, -1.6, Z0), (0, 0, 0.8), 0.42)
    import_model('street_lamp_01', (3.4, -3.8, Z0), (0, 0, math.radians(90)))
    import_model('potted_plant_02', (-2.2, -0.7, Z0), (0, 0, 2.0), 1.1)

    cameras()
    return sc


def cam(name, lens, f_stop=None, focus=None):
    c = bpy.data.cameras.new(name); c.lens = lens; c.sensor_fit = 'VERTICAL'; c.sensor_height = 24 * 16 / 9 * 0.75
    c.clip_start = 0.02
    if f_stop:
        c.dof.use_dof = True; c.dof.aperture_fstop = f_stop
        if focus: c.dof.focus_distance = focus
    return link(bpy.data.objects.new(name, c))


def path(obj, keys, target_keys=None, interp='BEZIER'):
    """keys: [(frame, (x,y,z), (tx,ty,tz))]: position and look-at target per key."""
    for f, p, t in keys:
        obj.location = p; look_at(obj, t)
        obj.keyframe_insert('location', frame=f); obj.keyframe_insert('rotation_euler', frame=f)


def cameras():
    sc = bpy.context.scene; Z0 = 0.15; TOP = Z0 + 0.95; CY = 3.1
    c1 = cam('S1', 30, 4.0, 7.0)
    path(c1, [(S1[0], (0.35, -7.6, 1.05), (0.05, 0, 1.55)), (S1[1], (0.15, -5.7, 1.25), (0.05, 0, 1.5))])
    c2 = cam('S2', 26, 2.8, 2.0)
    path(c2, [(S2[0], (-2.3, 1.15, 1.45), (-1.3, CY, 1.25)), (S2[1], (-0.5, 1.2, 1.5), (0.4, CY + 0.6, 1.5))])
    c3 = cam('S3', 50, 2.2, 0.36)
    ph = (0.55, CY - 0.14, TOP)
    path(c3, [(S3[0], (0.56, CY - 0.40, TOP + 0.34), ph), (S3[1], (0.555, CY - 0.30, TOP + 0.27), ph)])
    c3.data.dof.focus_object = bpy.data.objects['phone']
    c4 = cam('S4', 45, 2.4, 0.8)
    lt = (1.27, CY - 0.0, TOP + 0.12)
    path(c4, [(S4[0], (1.95, CY - 0.75, TOP + 0.24), lt), (S4[1], (1.52, CY - 0.62, TOP + 0.15), lt)])
    c4.data.dof.focus_object = bpy.data.objects['lap_screen']
    c5 = cam('S5', 35, 1.8, 0.9)
    sg = (1.11, 0.07, Z0 + 1.62)
    path(c5, [(S5[0], (0.9, -1.45, 1.62), sg), (FLIP[1] + 4, (1.05, -1.0, 1.72), (sg[0] + 0.01, sg[1], sg[2])), (S5[1], (1.1255, -0.74, Z0 + 1.63), (sg[0] + 0.0155, sg[1], sg[2]))])
    c5.data.dof.focus_object = bpy.data.objects['sign']
    for c, f in ((c1, S1[0]), (c2, S2[0]), (c3, S3[0]), (c4, S4[0]), (c5, S5[0])):
        m = sc.timeline_markers.new(c.name, frame=f); m.camera = c
    sc.camera = c1
    for f, ev in ((S1[0], 0.0), (S2[0], 0.8), (S3[0], 0.5), (S4[0], 0.5), (S5[0], 0.1)):
        sc.view_settings.exposure = ev; sc.view_settings.keyframe_insert('exposure', frame=f)
    set_interp(sc, 'CONSTANT')


def make_sign_textures():
    from PIL import Image, ImageDraw, ImageFont
    os.makedirs(P('build/tex'), exist_ok=True)
    W, H = 1200, 600
    for name, bg, fg, text in (('closed', (247, 245, 240), (24, 40, 42), 'Closed'), ('open', (17, 94, 103), (247, 245, 240), 'Open')):
        im = Image.new('RGB', (W, H), bg); d = ImageDraw.Draw(im)
        d.rounded_rectangle((24, 24, W - 24, H - 24), 40, outline=fg, width=10)
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 230)
        tw = d.textlength(text, font=f); bb = d.textbbox((0, 0), text, font=f)
        d.text(((W - tw) / 2, (H - (bb[3] - bb[1])) / 2 - bb[1]), text, font=f, fill=fg)
        if name == 'open':
            d.rounded_rectangle((W / 2 - 90, H - 120, W / 2 + 90, H - 104), 8, fill=(242, 182, 109))
        im.save(P('build/tex/sign_%s.png' % name))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--frames', default='0'); ap.add_argument('--res', type=float, default=0.8)
    ap.add_argument('--samples', type=int, default=40); ap.add_argument('--out', default=P('build/frames3d'))
    ap.add_argument('--threads', type=int, default=0); ap.add_argument('--blend', default='build/shop.blend')
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    make_sign_textures()
    sc = build()
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1920; sc.render.resolution_percentage = int(a.res * 100)
    sc.cycles.samples = a.samples; sc.cycles.adaptive_threshold = 0.04
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '16'
    if a.threads: sc.render.threads_mode = 'FIXED'; sc.render.threads = a.threads
    bpy.ops.wm.save_as_mainfile(filepath=P(a.blend))
    if a.frames == 'none': sys.exit(0)
    fr = []
    for part in a.frames.split(','):
        if '-' in part: s, e = map(int, part.split('-')); fr += list(range(s, e + 1))
        else: fr.append(int(part))
    os.makedirs(a.out, exist_ok=True)
    import time
    for f in fr:
        t = time.time(); sc.frame_set(f)
        sc.render.filepath = os.path.join(a.out, 'r%04d.png' % f)
        bpy.ops.render.render(write_still=True)
        print('FRAME %d %.1fs' % (f, time.time() - t), flush=True)
