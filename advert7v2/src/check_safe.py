"""Safe zone check for advert 7 v2. Projects every readable text region (phone notification, laptop
headline, door sign words) through the Blender camera of its shot, per frame, plus the end card layout.
Run with the bpy python."""
import bpy, json, os, sys
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.dirname(__file__))
from timing import *
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT, sys.argv[-1] if sys.argv[-1].endswith('.blend') else 'build/shop.blend'))
sc = bpy.context.scene; W, H = 1080, 1920; SAFE = (96, 154, 904, 1536); MIN_H = 14
B = json.load(open(os.path.join(ROOT, 'build/screen_boxes.json')))
def plane_pt(obj, u, v):
    """u, v in 0..1 across the plane (u left to right, v top to bottom of the image)."""
    me = obj.data; xs = [p.co.x for p in me.vertices]; ys = [p.co.y for p in me.vertices]
    x = min(xs) + (max(xs) - min(xs)) * u; y = max(ys) - (max(ys) - min(ys)) * v
    return obj.matrix_world @ Vector((x, y, 0))
regions = {
  'phone_title': ('phone_screen', [B['note']['nt'][0] / 390, B['note']['nt'][1] / 844, B['note']['nt'][2] / 390, B['note']['nt'][3] / 844], S3, NOTE + 6),
  'phone_body': ('phone_screen', [B['note']['nb'][0] / 390, B['note']['nb'][1] / 844, B['note']['nb'][2] / 390, B['note']['nb'][3] / 844], S3, NOTE + 6),
  'laptop_headline': ('lap_screen', [B['headline'][0] / 1600, B['headline'][1] / 1000, B['headline'][2] / 1600, B['headline'][3] / 1000], S4, SITE_LOAD + 8),
}
viol = []; seen = {}
for name, (oname, (u0, v0, u1, v1), (fa, fb), visible_from) in regions.items():
    ob = bpy.data.objects[oname]
    for f in range(max(fa, visible_from), fb):
        sc.frame_set(f); cam = sc.camera
        pts = []
        for u, v in ((u0, v0), (u1, v0), (u1, v1), (u0, v1)):
            c = world_to_camera_view(sc, cam, plane_pt(ob, u, v)); pts.append((c.x * W, (1 - c.y) * H))
        hgt = abs(pts[3][1] - pts[0][1])
        if hgt < MIN_H: continue
        seen.setdefault(name, []).append(f)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        if min(xs) < SAFE[0] or max(xs) > SAFE[2] or min(ys) < SAFE[1] or max(ys) > SAFE[3]:
            viol.append((f, name, [round(v) for v in (min(xs), min(ys), max(xs), max(ys))]))
# door sign word: the Open/Closed lettering occupies the middle 80 percent of the card
sign = bpy.data.objects['sign']
for f in range(S5[0], S5[1]):
    sc.frame_set(f); cam = sc.camera; pts = []
    for dx, dz in ((-0.12, -0.04), (0.12, -0.04), (0.12, 0.04), (-0.12, 0.04)):
        c = world_to_camera_view(sc, cam, sign.matrix_world @ Vector((dx, 0, dz))); pts.append((c.x * W, (1 - c.y) * H))
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    seen.setdefault('sign_word', []).append(f)
    if min(xs) < SAFE[0] or max(xs) > SAFE[2] or min(ys) < SAFE[1] or max(ys) > SAFE[3]:
        viol.append((f, 'sign_word', [round(v) for v in (min(xs), min(ys), max(xs), max(ys))]))
for k, v in seen.items(): print('%-16s readable frames %d..%d' % (k, v[0], v[-1]))
from collections import Counter
print('violations:', dict(Counter(v[1] for v in viol)))
for k in dict(Counter(v[1] for v in viol)): print('  e.g.', [v for v in viol if v[1] == k][:3])
