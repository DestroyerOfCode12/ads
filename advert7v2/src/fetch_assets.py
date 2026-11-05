"""Downloads the CC0 Poly Haven assets used by the scene (textures 2k, models 2k glTF, one HDRI)."""
import json, os, sys, urllib.request
_op = urllib.request.build_opener(); _op.addheaders = [('User-Agent', 'advert-build/1.0')]; urllib.request.install_opener(_op)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEX = ['white_oak_veneer', 'long_white_tiles', 'white_plaster_02', 'terrazzo_tiles', 'concrete_floor_worn_001',
       'whitewashed_brick', 'white_planks_clean', 'asphalt_02']
MODELS = ['rollershutter_door', 'croissant', 'carrot_cake', 'potted_plant_02', 'hanging_industrial_lamp',
          'wooden_display_shelves_01', 'tea_set_01', 'jug_01', 'wooden_cutting_board', 'cheiridopsis_succulent',
          'ceramic_vase_02', 'jacaranda_tree', 'street_lamp_01', 'strawberry_chocolate_cake', 'wicker_basket_01']
HDRI = 'bryanston_park_sunrise'
def get(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0: return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    urllib.request.urlretrieve(url, path)
def files(a): return json.load(urllib.request.urlopen('https://api.polyhaven.com/files/' + a))
for t in TEX:
    f = files(t)
    for k, name in (('Diffuse', 'diff'), ('nor_gl', 'nor'), ('Rough', 'rough')):
        get(f[k]['2k']['jpg']['url'], os.path.join(ROOT, 'assets/tex', t, name + '.jpg'))
    print('tex', t)
for m in MODELS:
    f = files(m)['gltf']; res = '2k' if '2k' in f else sorted(f)[0]
    g = f[res]['gltf']; d = os.path.join(ROOT, 'assets/models', m)
    get(g['url'], os.path.join(d, os.path.basename(g['url'])))
    for rel, inc in g.get('include', {}).items():
        get(inc['url'], os.path.join(d, rel))
    print('model', m, res)
f = files(HDRI)['hdri']
get(f['4k']['hdr']['url'], os.path.join(ROOT, 'assets/hdri', HDRI + '_4k.hdr'))
print('hdri ok')
