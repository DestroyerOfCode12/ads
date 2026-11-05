"""Advert 8, Open all hours: reuses advert 7's Blender shop set (advert7v2/src/scene.py) and
re-animates it: sunset time lapse, shutter down, night lit by the screens, a wall clock running
through the night, dawn, shutter up, sign flip. No people anywhere.

Run with the bpy venv:  python src/scene8.py --frames 0-403 [--res 0.6] [--samples 12]
"""
import bpy, bmesh, math, os, sys, argparse
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
A7 = os.path.abspath(os.path.join(ROOT, '..', 'advert7v2', 'src'))
sys.path.insert(0, HERE); sys.path.insert(1, A7)
import timing8 as T
import scene as S7   # advert 7 set builder (its own paths point at advert7v2/assets)

P = lambda *a: os.path.join(ROOT, *a)
Z0, CY = 0.15, 3.1
TOP = Z0 + 0.95


def kf(idb, path, frame, value, index=-1):
    attr = path
    if index >= 0:
        v = list(getattr(idb, attr)); v[index] = value; setattr(idb, attr, v)
    else:
        setattr(idb, attr, value)
    idb.keyframe_insert(attr, index=index, frame=frame)


def clear_v7_animation(sc):
    for o in bpy.data.objects:
        if o.animation_data: o.animation_data_clear()
    for l in bpy.data.lights:
        if l.animation_data: l.animation_data_clear()
    for m in bpy.data.materials:
        if m.node_tree and m.node_tree.animation_data: m.node_tree.animation_data_clear()
    if sc.animation_data: sc.animation_data_clear()
    for name in ('S1', 'S2', 'S3', 'S4', 'S5'):
        if name in bpy.data.objects: bpy.data.objects.remove(bpy.data.objects[name])
    sc.timeline_markers.clear()


def repoint_screens():
    for im in bpy.data.images:
        if im.source != 'SEQUENCE': continue
        if os.path.basename(im.filepath).startswith('p_'):
            im.filepath = P('build/tex/phone/p_0000.png')
        elif os.path.basename(im.filepath).startswith('l_'):
            im.filepath = P('build/tex/laptop/l_0000.png')
        im.reload()
    for mn in ('phone_screen', 'lap_screen'):
        for n in bpy.data.materials[mn].node_tree.nodes:
            if n.type == 'TEX_IMAGE':
                n.image_user.frame_duration = T.N3D; n.image_user.frame_start = 0; n.image_user.frame_offset = 0


def world_day_night(sc):
    w = sc.world; nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(S7.P('assets/hdri/bryanston_park_sunrise_4k.hdr'), check_existing=True)
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, math.radians(200))
    nt.links.new(tc.outputs['Generated'], mp.inputs[0]); nt.links.new(mp.outputs[0], env.inputs[0])
    tint = nt.nodes.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs['Factor'].default_value = 1
    nt.links.new(env.outputs[0], tint.inputs['A'])
    day = nt.nodes.new('ShaderNodeBackground'); day.inputs[1].default_value = 0.9
    nt.links.new(tint.outputs['Result'], day.inputs[0])
    night = nt.nodes.new('ShaderNodeBackground'); night.inputs[0].default_value = (0.010, 0.016, 0.040, 1); night.inputs[1].default_value = 1.0
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(day.outputs[0], mix.inputs[1]); nt.links.new(night.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
    fac = mix.inputs[0]; col = tint.inputs['B']
    for f, v in ((0, 0.0), (int(T.SUNSET[1] * 0.5), 0.35), (T.SUNSET[1], 1.0), (T.SUNRISE[0], 1.0), (T.SUNRISE[1], 0.0)):
        fac.default_value = v; fac.keyframe_insert('default_value', frame=f)
    for f, c in ((0, (1.0, 0.92, 0.82)), (int(T.SUNSET[1] * 0.7), (1.0, 0.55, 0.38)), (T.SUNRISE[0], (0.9, 0.6, 0.5)), (T.SUNRISE[1] + 20, (1.0, 0.9, 0.8))):
        col.default_value = (*c, 1); col.keyframe_insert('default_value', frame=f)


def sun_cycle():
    so = bpy.data.objects['sun']; sl = so.data
    # sunset from the right (shadows sweep left), sunrise from the left
    keys = [(0, 4.2, (1.0, 0.72, 0.48), 74, 38), (int(T.SUNSET[1] * 0.6), 3.0, (1.0, 0.5, 0.25), 82, 46),
            (T.SUNSET[1], 0.0, (1.0, 0.35, 0.15), 91, 52), (T.SUNRISE[0], 0.0, (1.0, 0.5, 0.3), 91, -64),
            (T.SUNRISE[1], 3.2, (1.0, 0.68, 0.45), 81, -56), (T.N3D, 4.2, (1.0, 0.78, 0.55), 77, -52)]
    for f, e, c, rx, rz in keys:
        sl.energy = e; sl.keyframe_insert('energy', frame=f)
        sl.color = c; sl.keyframe_insert('color', frame=f)
        so.rotation_euler = Euler((math.radians(rx), 0, math.radians(rz))); so.keyframe_insert('rotation_euler', frame=f)
    # avoid the sun swinging round between the two halves of the day
    S7.set_interp(so, 'BEZIER')
    for fc in S7.fcurves_of(so):
        for kp in fc.keyframe_points:
            if int(kp.co[0]) == T.SUNSET[1]: kp.interpolation = 'CONSTANT'


def shutter():
    cur = bpy.data.objects['curtain']; up = Z0 + 2.65 + 0.02
    for f, z in ((0, up), (T.SHUTTER_DOWN[0], up), (T.SHUTTER_DOWN[1], Z0), (T.SHUTTER_UP[0], Z0), (T.SHUTTER_UP[1], up)):
        cur.location.z = z; cur.keyframe_insert('location', index=2, frame=f)
    S7.set_interp(cur, 'SINE', 'EASE_IN_OUT')


def shop_lights():
    bulbs = [l for l in bpy.data.lights if l.name.startswith('bulb')]; fill = bpy.data.lights['fill']
    off = T.LIGHTS_OFF; on = T.LIGHTS_ON
    pattern = [(0, 1.0), (off, 1.0), (off + 1, 0.0), (off + 2, 0.4), (off + 3, 0.0), (on, 0.0), (on + 1, 1.0), (on + 2, 0.15),
               (on + 4, 0.9), (on + 5, 0.3), (on + 7, 1.0), (T.N3D, 1.0)]
    for lt, full in [(b, 130.0) for b in bulbs] + [(fill, 650.0)]:
        for f, v in pattern: lt.energy = full * v; lt.keyframe_insert('energy', frame=f)
        S7.set_interp(lt, 'CONSTANT')
    em = bpy.data.materials['bulb_glow'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    for f, v in pattern: em.default_value = 40 * v; em.keyframe_insert('default_value', frame=f)
    S7.set_interp(bpy.data.materials['bulb_glow'].node_tree, 'CONSTANT')
    # night: a dim cool ambience inside (street light leaking through the shutter slats)
    nl = bpy.data.lights.new('night_ambient', 'AREA'); nl.size = 3.0; nl.color = (0.55, 0.68, 1.0)
    no = S7.link(bpy.data.objects.new('night_ambient', nl)); no.location = (0, 1.0, Z0 + 2.4); no.rotation_euler = (math.radians(60), 0, 0)
    for f, v in ((0, 0), (T.SHUTTER_DOWN[1] - 4, 0), (T.SHUTTER_DOWN[1] + 4, 1), (T.SHUTTER_UP[0], 1), (T.SHUTTER_UP[0] + 20, 0)):
        nl.energy = 70 * v; nl.keyframe_insert('energy', frame=f)
    # screen glow so the laptop and phone light their surroundings at night
    for parent, size, energy, col, frames in (('lap_screen', (0.28, 0.18), 5.0, (0.75, 0.9, 0.95), [(0, 1), (T.N3D, 1)]),
                                              ('phone_screen', (0.07, 0.15), 1.2, (0.6, 0.85, 0.9), [(0, 0), (T.WAKE, 0), (T.WAKE + 6, 1), (T.S3[0], 1), (T.S3[0] + 1, 0)])):
        g = bpy.data.lights.new(parent + '_glow', 'AREA'); g.shape = 'RECTANGLE'; g.size, g.size_y = size; g.color = col
        go = S7.link(bpy.data.objects.new(parent + '_glow', g)); go.parent = bpy.data.objects[parent]
        go.location = (0, 0, 0.004); go.rotation_euler = (math.radians(180), 0, 0)   # emit away from the screen face
        for f, v in frames: g.energy = energy * v; g.keyframe_insert('energy', frame=f)


def street_lamp():
    root = bpy.data.objects['street_lamp_01_root']
    pts = []
    for o in root.children_recursive:
        if o.type == 'MESH':
            pts += [o.matrix_world @ v.co for v in o.data.vertices]
    zmax = max(p.z for p in pts); head = [p for p in pts if p.z > zmax - 0.35]
    c = sum(head, Vector()) / len(head)
    lt = bpy.data.lights.new('street_lamp', 'SPOT'); lt.spot_size = math.radians(110); lt.spot_blend = 0.6
    lt.color = (1.0, 0.82, 0.6); lt.shadow_soft_size = 0.15
    lo = S7.link(bpy.data.objects.new('street_lamp', lt)); lo.location = (c.x, c.y, zmax - 0.25); lo.rotation_euler = (0, 0, 0)
    glow = S7.simple('lamp_glow', (1, 0.9, 0.7), 0.3, emit=(1.0, 0.82, 0.6), emit_strength=0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.07, location=(c.x, c.y, zmax - 0.2)); bpy.context.object.data.materials.append(glow)
    es = glow.node_tree.nodes['Principled BSDF'].inputs['Emission Strength']
    on = T.LAMP_ON
    for f, v in ((0, 0), (on, 0), (on + 1, 0.7), (on + 2, 0.1), (on + 4, 1), (on + 5, 0.4), (on + 6, 1), (T.SUNRISE[0] + 20, 1), (T.SUNRISE[0] + 21, 0)):
        lt.energy = 900 * v; lt.keyframe_insert('energy', frame=f)
        es.default_value = 60 * v; es.keyframe_insert('default_value', frame=f)
    S7.set_interp(lt, 'CONSTANT'); S7.set_interp(glow.node_tree, 'CONSTANT')


def wall_clock():
    """Simple wall clock on the back wall; hands driven by the night time lapse."""
    cx, cz, wy = 0.95, Z0 + 2.4, 5.595; R = 0.2
    face = S7.simple('clock_face', (0.93, 0.92, 0.88), 0.5); rim = S7.simple('clock_rim', (0.02, 0.03, 0.03), 0.35, 0.6)
    ink = S7.simple('clock_ink', (0.02, 0.025, 0.03), 0.5); red = S7.simple('clock_sec', S7.APRICOT, 0.4)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=R + 0.018, depth=0.04, location=(cx, wy - 0.02, cz), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(rim)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=R, depth=0.01, location=(cx, wy - 0.042, cz), rotation=(math.radians(90), 0, 0))
    bpy.context.object.data.materials.append(face)
    for i in range(12):
        a = i / 12 * 2 * math.pi; big = i % 3 == 0
        tk = S7.box('tick', (0.012 if big else 0.006, 0.003, 0.04 if big else 0.025), (cx + math.sin(a) * (R - 0.035), wy - 0.049, cz + math.cos(a) * (R - 0.035)), ink)
        tk.rotation_euler = (0, -a, 0)
    hands = {}
    for name, length, width, mat in (('hour', 0.11, 0.014, ink), ('minute', 0.165, 0.009, ink)):
        piv = bpy.data.objects.new('clock_' + name, None); S7.link(piv); piv.location = (cx, wy - 0.052 - (0.002 if name == 'minute' else 0), cz)
        h = S7.box('hand_' + name, (width, 0.002, length), (0, 0, length / 2 - 0.02), mat); h.parent = piv
        hands[name] = piv
    cap = S7.box('clock_cap', (0.018, 0.004, 0.018), (cx, wy - 0.056, cz), red)
    f0, f1, h0, h1 = T.CLOCK
    for f, hrs in ((0, h0), (f0, h0), (f1, h1), (T.N3D, h1 + (T.N3D - f1) / (f1 - f0) * (h1 - h0) * 0.15)):
        hands['minute'].rotation_euler.y = (hrs % 1) * 2 * math.pi + math.floor(hrs) * 2 * math.pi
        hands['minute'].keyframe_insert('rotation_euler', index=1, frame=f)
        hands['hour'].rotation_euler.y = hrs / 12 * 2 * math.pi
        hands['hour'].keyframe_insert('rotation_euler', index=1, frame=f)
    for h in hands.values(): S7.set_interp(h, 'LINEAR')


def phone_buzz():
    ph = bpy.data.objects['phone']; x0 = ph.location.x
    for i, f in enumerate(range(T.BUZZ - 2, T.BUZZ + 10)):
        j = 0 if f in (T.BUZZ - 2, T.BUZZ + 9) else (0.0016 if i % 2 else -0.0016)
        ph.location.x = x0 + j; ph.keyframe_insert('location', index=0, frame=f)
        ph.rotation_euler.z = math.radians((0.6 if i % 2 else -0.6) * (j != 0)); ph.keyframe_insert('rotation_euler', index=2, frame=f)


def sign_flip():
    sign = bpy.data.objects['sign']; a, b = T.FLIP
    for f, z in ((0, 0), (a, 0), (a + 9, -194), (a + 14, -174), (b, -180)):
        sign.rotation_euler.z = math.radians(z); sign.keyframe_insert('rotation_euler', index=2, frame=f)


def cameras(sc):
    cam, path = S7.cam, S7.path
    c1 = cam('C1', 30, 4.0, 7.0)
    path(c1, [(T.S1[0], (0.45, -8.2, 2.9), (0.05, 0, 1.75)), (T.S1[1], (0.15, -6.0, 1.25), (0.05, 0, 1.45))])
    c2 = cam('C2', 40, 2.8, 3.4)
    lt = (1.27, CY - 0.0, TOP + 0.12)
    path(c2, [(T.S2A[0], (0.55, 2.0, 1.95), (0.95, 5.59, Z0 + 2.4)), (T.S2A[0] + 30, (0.75, 2.05, 1.85), (0.98, 5.59, Z0 + 2.3)),
              (T.S2A[1], (1.62, 2.3, 1.3), lt)])
    c2.data.dof.focus_object = bpy.data.objects['clock_cap']
    # refocus from the clock to the laptop as the camera arrives
    for f, fo in ((T.S2A[0] + 34, 'clock_cap'), (T.S2A[0] + 35, 'lap_screen')):
        pass
    c3 = cam('C3', 50, 2.2, 0.36); ph = (0.55, CY - 0.14, TOP)
    path(c3, [(T.S2B[0], (0.56, CY - 0.40, TOP + 0.34), ph), (T.S2B[1], (0.555, CY - 0.30, TOP + 0.27), ph)])
    c3.data.dof.focus_object = bpy.data.objects['phone']
    c4 = cam('C4', 28, 3.2, 3.6)
    path(c4, [(T.S3[0], (0.95, 5.0, 1.6), (0.2, 0.0, 1.3)), (T.S3[1], (0.65, 4.3, 1.5), (0.2, 0.0, 1.35))])
    c5 = cam('C5', 35, 1.8, 0.9); sg = (1.11, 0.07, Z0 + 1.62)
    path(c5, [(T.S4[0], (0.9, -1.45, 1.62), sg), (T.FLIP[1] + 4, (1.05, -1.0, 1.72), (sg[0] + 0.01, sg[1], sg[2])),
              (T.S4[1], (1.1255, -0.74, Z0 + 1.63), (sg[0] + 0.0155, sg[1], sg[2]))])
    c5.data.dof.focus_object = bpy.data.objects['sign']
    for c, f in ((c1, T.S1[0]), (c2, T.S2A[0]), (c3, T.S2B[0]), (c4, T.S3[0]), (c5, T.S4[0])):
        m = sc.timeline_markers.new(c.name, frame=f); m.camera = c
    sc.camera = c1
    # exposure per shot, rising through the sunset so the street stays readable
    for f, ev in ((0, 0.0), (T.SUNSET[1], 1.3), (T.S2A[0], 0.85), (T.S2B[0], 0.55), (T.S3[0], 1.2), (T.S3[0] + 40, 0.6), (T.S4[0], 0.1)):
        sc.view_settings.exposure = ev; sc.view_settings.keyframe_insert('exposure', frame=f)
    for fc in S7.fcurves_of(sc):
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT' if int(kp.co[0]) in (T.S2A[0], T.S2B[0], T.S3[0], T.S4[0]) else 'BEZIER'


def build():
    sc = S7.build()
    clear_v7_animation(sc)
    repoint_screens()
    world_day_night(sc); sun_cycle(); shutter(); shop_lights(); street_lamp(); wall_clock(); phone_buzz(); sign_flip()
    cameras(sc)
    # refocus C2 from the clock to the laptop during the move (DOF focus distance keys)
    c2 = bpy.data.objects['C2']; c2.data.dof.focus_object = None
    for f, d in ((T.S2A[0], 3.45), (T.S2A[0] + 30, 3.45), (T.S2A[1] - 8, 0.8), (T.S2A[1], 0.78)):
        c2.data.dof.focus_distance = d; c2.data.dof.keyframe_insert('focus_distance', frame=f)
    sc.render.use_motion_blur = True; sc.render.motion_blur_shutter = 0.4
    return sc


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--frames', default='0'); ap.add_argument('--res', type=float, default=0.6)
    ap.add_argument('--samples', type=int, default=12); ap.add_argument('--night_samples', type=int, default=16)
    ap.add_argument('--out', default=P('build/frames3d')); ap.add_argument('--blend', default=P('build/shop8.blend'))
    a = ap.parse_args(sys.argv[1:])
    sc = build()
    sc.render.resolution_x, sc.render.resolution_y = 1080, 1920; sc.render.resolution_percentage = int(a.res * 100)
    sc.cycles.adaptive_threshold = 0.04
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '16'
    bpy.ops.wm.save_as_mainfile(filepath=a.blend)
    if a.frames == 'none': sys.exit(0)
    fr = []
    for part in a.frames.split(','):
        if '-' in part: s, e = map(int, part.split('-')); fr += list(range(s, e + 1))
        else: fr.append(int(part))
    os.makedirs(a.out, exist_ok=True)
    import time
    for f in fr:
        out = os.path.join(a.out, 'r%04d.png' % f)
        if os.path.exists(out) and os.path.getsize(out) > 0: continue     # resumable after a restart
        t = time.time(); sc.frame_set(f)
        sc.cycles.samples = a.night_samples if T.SHUTTER_DOWN[1] <= f < T.SHUTTER_UP[0] else a.samples
        sc.render.filepath = out
        bpy.ops.render.render(write_still=True)
        print('FRAME %d %.1fs' % (f, time.time() - t), flush=True)
