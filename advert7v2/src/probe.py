import bpy, os, glob, mathutils
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
for d in sorted(glob.glob(os.path.join(ROOT, 'assets/models/*'))):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    g = glob.glob(d + '/*.gltf')[0]
    bpy.ops.import_scene.gltf(filepath=g)
    obs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    mn = mathutils.Vector((1e9,) * 3); mx = -mn
    for o in obs:
        for c in o.bound_box:
            w = o.matrix_world @ mathutils.Vector(c); mn = mathutils.Vector(map(min, mn, w)); mx = mathutils.Vector(map(max, mx, w))
    tris = sum(len(o.data.polygons) for o in obs)
    print('%-28s meshes %2d polys %7d size %s min %s' % (os.path.basename(d), len(obs), tris, tuple(round(v, 3) for v in mx - mn), tuple(round(v, 3) for v in mn)), [o.name for o in obs][:6])
