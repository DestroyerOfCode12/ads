"""Averages the sub frame samples into final frames (motion blur). python3 src/blend.py [--frames ...]"""
import glob, os, re, sys
import numpy as np
from PIL import Image
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.makedirs(os.path.join(R, 'build/frames'), exist_ok=True)
groups = {}
for p in glob.glob(os.path.join(R, 'build/sub/f*_*.png')):
    f = int(re.search(r'f(\d+)_', p).group(1)); groups.setdefault(f, []).append(p)
want = None
if '--frames' in sys.argv: want = set(map(int, sys.argv[sys.argv.index('--frames') + 1].split(',')))
for f, ps in sorted(groups.items()):
    if want and f not in want: continue
    acc = sum(np.asarray(Image.open(p).convert('RGB')).astype(np.float32) ** 2.2 for p in ps) / len(ps)   # average in linear light
    Image.fromarray(np.clip(acc ** (1 / 2.2), 0, 255).astype(np.uint8)).save(os.path.join(R, 'build/frames/f%04d.png' % f), compress_level=1)
print('blended', len(groups))
