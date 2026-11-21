"""Composites the photoreal plates, the rendered UI and the end card into 480 frames.

Usage: python3 src/composite.py [--frames 0,120,200] [--out build/frames]
"""
import json, math, os, sys, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from timeline import *

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
P = lambda *a: os.path.join(ROOT, *a)
W, H = 1080, 1920
SAFE = dict(x0=96, x1=1080 - 176, y0=154, y1=1536)
TEAL = (0x11, 0x5E, 0x67); WARM = (0xF7, 0xF5, 0xF0); MIST = (0xD9, 0xEC, 0xEC)
INK = (0x18, 0x28, 0x2A); APRICOT = (0xF2, 0xB6, 0x6D)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

# screen quads in plate pixels (TL, TR, BR, BL), measured by src/detect.py
LAP_Q = np.array([(1139, 1864), (2830, 2121), (2618, 3368), (1011, 3032)], float)
# phone: right corner is off frame; extrapolated as top + bottom - left
_top, _bot, _left = np.array((2764, 3645.)), np.array((2703, 4249.)), np.array((2344, 4087.))
PH_Q = np.array([_top, _top + _bot - _left, _bot, _left], float)
UI_W, UI_H = 1600, 1000
PHUI_W, PHUI_H = 780, 1688


def homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(A))
    h = vt[-1].reshape(3, 3)
    return h / h[2, 2]


def rect(w, h): return np.array([(0, 0), (w, 0), (w, h), (0, h)], float)
H_LAP = homography(rect(UI_W, UI_H), LAP_Q)
H_PH = homography(rect(PHUI_W, PHUI_H), PH_Q)


def apply_h(h, pts):
    pts = np.asarray(pts, float)
    p = np.c_[pts, np.ones(len(pts))] @ h.T
    return p[:, :2] / p[:, 2:3]


# ---------------------------------------------------------------- plates
def load_plate():
    cache = P('build/plate_prepped.npz')
    if os.path.exists(cache):
        z = np.load(cache); return z['im'], z['alpha']
    im, alpha = _prep_plate()
    np.savez(cache, im=im, alpha=alpha)
    return im, alpha


def _grow(mask_img, r):
    """Fast binary dilation: max filter at 1/8 scale, then back up."""
    w, h = mask_img.size
    sm = mask_img.resize((w // 8, h // 8), Image.BOX).point(lambda v: 255 if v > 0 else 0)
    k = 2 * max(1, r // 8) + 1
    return sm.filter(ImageFilter.MaxFilter(k)).resize((w, h), Image.NEAREST)


def _prep_plate():
    im = np.asarray(Image.open(P('assets/desk.png')).convert('RGB')).astype(np.float32)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    green = ((g > 120) & (g > r + 50) & (g > b + 50))
    gm = Image.fromarray((green * 255).astype(np.uint8))
    # alpha: screen area grown by 3 px then softened, so no green fringe survives
    alpha = np.asarray(gm.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    # despill a wider band around the screens (bezel reflections, keyboard glow)
    band = np.asarray(_grow(gm, 30)).astype(bool)
    lim = np.maximum(r, b) * 1.04 + 4
    spill = band & (g > lim)
    im[..., 1] = np.where(spill, lim, g)
    return im, alpha


def warp_into(dst, alpha_full, src, hmat, bbox, gain=1.0):
    """Inverse-map src (HxWx3 float) into dst over bbox using plate->src homography."""
    x0, y0, x1, y1 = bbox
    hi = np.linalg.inv(hmat)
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
    den = hi[2, 0] * xs + hi[2, 1] * ys + hi[2, 2]
    u = (hi[0, 0] * xs + hi[0, 1] * ys + hi[0, 2]) / den
    v = (hi[1, 0] * xs + hi[1, 1] * ys + hi[1, 2]) / den
    sh, sw = src.shape[:2]
    u = np.clip(u, 0, sw - 1.001); v = np.clip(v, 0, sh - 1.001)
    ui, vi = u.astype(np.int32), v.astype(np.int32)
    fu, fv = (u - ui)[..., None], (v - vi)[..., None]
    c = (src[vi, ui] * (1 - fu) * (1 - fv) + src[vi, ui + 1] * fu * (1 - fv)
         + src[vi + 1, ui] * (1 - fu) * fv + src[vi + 1, ui + 1] * fu * fv) * gain
    a = alpha_full[y0:y1, x0:x1, None]
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + c * a


def screen_look(img, w, h, glare=0.06):
    """Emissive screen: slight softening, gentle window glare from the left."""
    a = np.asarray(img.convert('RGB').filter(ImageFilter.GaussianBlur(0.5))).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    g = np.clip(1 - (xx / w * 0.9 + yy / h * 0.6), 0, 1) ** 2 * glare * 255
    a = a * 0.95 + g[..., None]
    return np.clip(a, 0, 255)


class Compositor:
    def __init__(self):
        self.plate, self.alpha = load_plate()
        self.fs = json.load(open(P('build/frame_states.json')))
        self.cache = {}
        self.phone_ui = screen_look(Image.open(P('build/phone_ui.png')), PHUI_W, PHUI_H, 0.08)
        self.trackpad = Image.open(P('assets/trackpad.png')).convert('RGB')
        lb = apply_h(H_LAP, rect(UI_W, UI_H)); pb = PH_Q
        self.lap_bb = (int(lb[:, 0].min()) - 6, int(lb[:, 1].min()) - 6, int(lb[:, 0].max()) + 7, int(lb[:, 1].max()) + 7)
        self.ph_bb = (int(pb[:, 0].min()) - 6, int(pb[:, 1].min()) - 6, min(3072, int(pb[:, 0].max()) + 7), int(pb[:, 1].max()) + 7)
        # dark phone screen: deep ink with a soft sky reflection
        yy, xx = np.mgrid[0:PHUI_H, 0:PHUI_W].astype(np.float32)
        refl = np.clip(1 - (xx / PHUI_W + yy / PHUI_H) * 0.8, 0, 1) ** 3 * 40
        self.phone_dark = np.stack([12 + refl, 14 + refl, 16 + refl * 1.05], -1)

    def plate_frame(self, f):
        key = self.fs[str(min(f, T_END))]
        pw = clamp((f - T_PHONE) / 8)
        pkey = (key, round(pw, 2))
        if pkey in self.cache: return self.cache[pkey]
        if len(self.cache) > 6: self.cache.clear()
        im = self.plate.copy()
        ui = screen_look(Image.open(P('build/ui/%s.png' % key)), UI_W, UI_H)
        warp_into(im, self.alpha, ui, H_LAP, self.lap_bb)
        ph = self.phone_dark * (1 - pw) + self.phone_ui * pw
        warp_into(im, self.alpha, ph, H_PH, self.ph_bb)
        out = Image.fromarray(np.clip(im, 0, 255).astype(np.uint8))
        self.cache[pkey] = out
        return out


# ---------------------------------------------------------------- camera
ROLL = math.atan2(LAP_Q[1, 1] - LAP_Q[0, 1], LAP_Q[1, 0] - LAP_Q[0, 0])  # screen tilt


def rot(t): return np.array([[math.cos(t), -math.sin(t)], [math.sin(t), math.cos(t)]])


def fit(ux0, ux1, uy, ox0, ox1, oy, roll):
    """Camera (centre plate xy, scale out/plate, roll) placing UI span [ux0,ux1]@uy at output [ox0,ox1]@oy."""
    p0, p1 = apply_h(H_LAP, [(ux0, uy), (ux1, uy)])
    d = rot(-roll) @ (p1 - p0)
    s = (ox1 - ox0) / d[0]
    c = p0 - rot(roll) @ ((np.array([ox0, oy]) - (W / 2, H / 2)) / s)
    return (c[0], c[1], s, roll)


KF = {
    'wide': (1536, 2728, W / 3072, 0.0),
    'wide_in': (1640, 2700, W / 2700, ROLL * 0.15),
    'search': fit(400, 1200, 483, 80, 920, 900, ROLL * 0.85),
    'results': fit(140, 920, 470, SAFE['x0'], SAFE['x1'], 860, ROLL * 0.85),
    'site': fit(100, 1500, 480, SAFE['x0'], SAFE['x1'], 860, ROLL * 0.75),
    'site_in': fit(130, 1470, 470, SAFE['x0'], SAFE['x1'], 850, ROLL * 0.75),
    'wide_end': (1600, 2760, W / 3000, 0.0),
}
# camera track: (frame, keyframe); between entries we ease in and out
TRACK = [(0, 'wide'), (34, 'wide_in'), (80, 'search'), (116, 'search'), (146, 'results'),
         (T_INS0, 'results'), (T_INS1 - 1, 'results'), (T_INS1, 'site'), (T_PULL0, 'site_in'),
         (T_PULL1, 'wide_end'), (T_END + 20, 'wide_end')]


def cam(f):
    for (fa, ka), (fb, kb) in zip(TRACK, TRACK[1:]):
        if fa <= f <= fb:
            t = ease_io((f - fa) / max(1, fb - fa))
            a, b = KF[ka], KF[kb]
            s = math.exp(math.log(a[2]) * (1 - t) + math.log(b[2]) * t)
            # interpolate the centre in a scale-aware way so the move feels like a dolly
            cx = a[0] + (b[0] - a[0]) * t; cy = a[1] + (b[1] - a[1]) * t
            r = a[3] + (b[3] - a[3]) * t
            break
    # gentle handheld drift: a few output pixels, low frequency
    jx = 2.2 * math.sin(f * 0.071) + 1.3 * math.sin(f * 0.19 + 1.3)
    jy = 1.8 * math.sin(f * 0.057 + 0.7) + 1.1 * math.sin(f * 0.23)
    jr = 0.0009 * math.sin(f * 0.049 + 2)
    return cx + jx / s, cy + jy / s, s, r + jr


def out_to_plate_affine(c, ss=2):
    cx, cy, s, r = c
    # plate = C + R(r) @ ((o/ss - centre)/s)
    m = rot(r) / (s * ss)
    off = np.array([cx, cy]) - rot(r) @ (np.array([W / 2, H / 2]) / s)
    return (m[0, 0], m[0, 1], off[0], m[1, 0], m[1, 1], off[1])


def plate_to_out(c, pts):
    cx, cy, s, r = c
    pts = np.asarray(pts, float)
    return (rot(-r) @ (pts - (cx, cy)).T).T * s + (W / 2, H / 2)


def render_photo(comp, f, ss=2):
    c = cam(f)
    pl = comp.plate_frame(f)
    big = pl.transform((W * ss, H * ss), Image.AFFINE, out_to_plate_affine(c, ss), resample=Image.BICUBIC)
    img = big.resize((W, H), Image.LANCZOS)
    # shallow depth of field in close ups: focus on the screen, soften keyboard and hands
    k = clamp((c[2] - 0.45) / 0.25)
    if k > 0:
        bl, br = plate_to_out(c, LAP_Q[[3, 2]])
        yb = min(bl[1], br[1])
        blur = img.filter(ImageFilter.GaussianBlur(7 * k))
        yy = np.arange(H, dtype=np.float32)
        m = np.clip((yy - (yb + 30)) / 220, 0, 1)
        mask = Image.fromarray((np.repeat(m[:, None], W, 1) * 255).astype(np.uint8))
        img = Image.composite(blur, img, mask)
    return img, c


def render_insert(comp, f):
    t = (f - T_INS0) / (T_INS1 - T_INS0)
    w = 1420 - 170 * ease_io(t)
    bump = 1 + 0.012 * math.exp(-((f - T_CLICK) / 2.2) ** 2)   # tiny press on the click
    w /= bump
    h = w * H / W
    cx = clamp(780 + 40 * t, w / 2, 1536 - w / 2); cy = clamp(1290 + 50 * t, h / 2, 2736 - h / 2)
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    return comp.trackpad.resize((W, H), Image.LANCZOS, box=box)


def finish(img, f, grain=True, strength=1.0):
    a = np.asarray(img).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    v = 1 - 0.22 * strength * (((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2)
    a *= v[..., None]
    if grain:
        rng = np.random.default_rng(1000 + f)
        a += rng.normal(0, 2.4 * strength, (H, W, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- end card
def logo_white(target_w=560):
    """Stacked Nimble Tech Solutions lockup, white. Uses assets/logo_white.png when supplied."""
    path = P('assets/logo_white.png')
    if os.path.exists(path):
        lg = Image.open(path).convert('RGBA')
        return lg.resize((target_w, round(lg.height * target_w / lg.width)), Image.LANCZOS)
    big = Image.new('RGBA', (1400, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
    f1 = ImageFont.truetype(FONTB, 210); f2 = ImageFont.truetype(FONT, 92)
    l1 = 'Nimble'; l2 = 'Tech Solutions'
    w1 = d.textlength(l1, font=f1); w2 = d.textlength(l2, font=f2)
    d.text(((1400 - w1) / 2, 20), l1, font=f1, fill=(255, 255, 255, 255))
    d.text(((1400 - w2) / 2, 290), l2, font=f2, fill=(255, 255, 255, 255))
    # small apricot rule between the lines as a brand detail
    d.rounded_rectangle((700 - 70, 262, 700 + 70, 276), 7, fill=APRICOT + (255,))
    bb = big.getbbox(); big = big.crop(bb)
    return big.resize((target_w, round(big.height * target_w / big.width)), Image.LANCZOS)


END_CX = (SAFE['x0'] + SAFE['x1']) // 2  # centre of the safe zone, not of the frame
_LOGO = None
END_LINES = [('tag', 'Websites and digital services', FONT, 44, WARM, 930),
             ('wa', 'WhatsApp 068 178 9708', FONTB, 46, APRICOT, 1020),
             ('area', 'Midrand, Johannesburg, Remote', FONT, 38, MIST, 1104)]
SHAPES = [  # x, rest y, size, colour, kind, start delay
    (300, 300, 54, MIST, 'circle', 0), (430, 250, 30, APRICOT, 'circle', 3), (560, 320, 44, WARM, 'square', 5),
    (690, 262, 36, MIST, 'square', 2), (790, 330, 24, APRICOT, 'circle', 7), (210, 360, 22, WARM, 'circle', 8)]


def end_card(f):
    global _LOGO
    if _LOGO is None: _LOGO = logo_white(560)
    img = Image.new('RGBA', (W, H), TEAL + (255,))
    s0, s1 = END_ITEMS['shapes']
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for x, y, sz, col, kind, dl in SHAPES:
        t = clamp((f - s0 - dl) / (s1 - s0 - 8))
        e = 1 - (1 - t) ** 3 * math.cos(t * 2.2)   # settles with a slight overshoot
        yy = y - 220 * (1 - e); a = int(255 * 0.85 * smooth(t * 2.5))
        box = (x - sz / 2, yy - sz / 2, x + sz / 2, yy + sz / 2)
        if kind == 'circle': d.ellipse(box, fill=col + (a,))
        else: d.rounded_rectangle(box, sz * 0.28, fill=col + (a,))
    img.alpha_composite(lay)
    l0, l1 = END_ITEMS['logo']
    ta = smooth((f - l0) / (l1 - l0))
    if ta > 0:
        lg = _LOGO.copy(); lg.putalpha(lg.getchannel('A').point(lambda v: int(v * ta)))
        img.alpha_composite(lg, (END_CX - lg.width // 2, 640 - lg.height // 2 + round(14 * (1 - ta))))
    for key, text, font, size, col, y in END_LINES:
        a0, a1 = END_ITEMS[key]; ta = smooth((f - a0) / (a1 - a0))
        if ta <= 0: continue
        fo = ImageFont.truetype(font, size)
        tl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(tl)
        tw = dd.textlength(text, font=fo)
        dd.text((END_CX - tw / 2, y + round(10 * (1 - ta))), text, font=fo, fill=col + (int(255 * ta),))
        img.alpha_composite(tl)
    return img.convert('RGB')


def end_layout():
    """Bounding boxes of the final end card items, for the safe area check."""
    lg = logo_white(560); boxes = {'logo': (END_CX - lg.width // 2, 640 - lg.height // 2, END_CX + lg.width // 2, 640 + lg.height // 2)}
    d = ImageDraw.Draw(Image.new('RGB', (10, 10)))
    for key, text, font, size, col, y in END_LINES:
        fo = ImageFont.truetype(font, size); bb = d.textbbox((0, 0), text, font=fo)
        tw = d.textlength(text, font=fo)
        boxes[key] = (END_CX - tw / 2, y + bb[1], END_CX + tw / 2, y + bb[3])
    return boxes


# ---------------------------------------------------------------- frame
def frame(comp, f):
    if T_INS0 <= f < T_INS1:
        return finish(render_insert(comp, f), f)
    if f < T_END:
        return finish(render_photo(comp, f)[0], f)
    xf = smooth((f - T_END) / 12)
    card = end_card(f)
    if xf >= 1: return card
    ph = finish(render_photo(comp, f)[0], f)
    return Image.blend(ph, card, xf)


def worker(args):
    frames, outdir = args
    comp = Compositor()
    for f in frames:
        frame(comp, f).save(os.path.join(outdir, 'f%04d.png' % f), compress_level=1)
    return len(frames)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames'); ap.add_argument('--out', default=P('build/frames')); ap.add_argument('-j', type=int, default=4)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    fr = [int(x) for x in a.frames.split(',')] if a.frames else list(range(N))
    from multiprocessing import Pool
    # contiguous chunks so each worker's plate cache stays warm
    k = max(1, math.ceil(len(fr) / a.j)); chunks = [fr[i:i + k] for i in range(0, len(fr), k)]
    with Pool(len(chunks)) as pool:
        print(sum(pool.map(worker, [(c, a.out) for c in chunks])), 'frames')
