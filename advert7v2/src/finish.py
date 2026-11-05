"""Finishing pass: upscale the Cycles renders, grade, bloom, lens effects, grain, dust in the light,
then the redesigned end card. Writes build/frames/f%04d.png (1080x1920, 480 frames).

python3 src/finish.py [--frames 0,200,470] [-j 4]
"""
import os, sys, math, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
sys.path.insert(0, os.path.dirname(__file__))
from timing import *

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
P = lambda *a: os.path.join(ROOT, *a)
W, H = 1080, 1920
SAFE = dict(x0=96, x1=904, y0=154, y1=1536)
CX = (SAFE['x0'] + SAFE['x1']) // 2
TEAL = (0x11, 0x5E, 0x67); WARM = (0xF7, 0xF5, 0xF0); MIST = (0xD9, 0xEC, 0xEC); APRICOT = (0xF2, 0xB6, 0x6D)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
clamp = lambda v, a=0.0, b=1.0: max(a, min(b, v))
smooth = lambda x: (lambda t: t * t * (3 - 2 * t))(clamp(x))
YY, XX = np.mgrid[0:H, 0:W].astype(np.float32)
VIGN = (1 - 0.28 * (((XX - W / 2) / (W * 0.72)) ** 2 + ((YY - H / 2) / (H * 0.72)) ** 2))[..., None]


def load_render(f):
    im = Image.open(P('build/frames3d', 'r%04d.png' % f))
    a = np.asarray(im).astype(np.float32)
    a = a / (65535.0 if a.max() > 255 else 255.0)
    return a[..., :3]


def grade(a):
    # gentle split tone: cool teal shadows, warm highlights; soft S curve; touch more saturation
    lum = (a * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
    sh = np.clip(1 - lum * 2.2, 0, 1); hi = np.clip(lum * 1.6 - 0.6, 0, 1)
    a = a + sh * np.array([-0.012, 0.006, 0.014]) + hi * np.array([0.03, 0.012, -0.02])
    a = np.clip(a, 0, 1); a = a + 0.06 * np.sin((a - 0.5) * np.pi) * 0.5 * 2 / np.pi * np.pi / 2
    lum = (a * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
    return np.clip(lum + (a - lum) * 1.06, 0, 1)


def lens(img8, f):
    a = np.asarray(img8).astype(np.float32) / 255
    # bloom from highlights
    lum = (a * [0.2126, 0.7152, 0.0722]).sum(-1)
    hl = Image.fromarray((np.clip((lum - 0.78) / 0.22, 0, 1)[..., None] * a * 255).astype(np.uint8))
    bl = np.asarray(hl.filter(ImageFilter.GaussianBlur(22))).astype(np.float32) / 255
    bl2 = np.asarray(hl.filter(ImageFilter.GaussianBlur(6))).astype(np.float32) / 255
    a = 1 - (1 - a) * (1 - bl * 0.35) * (1 - bl2 * 0.2)
    # lateral chromatic aberration (tiny, radial)
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)); r, g, b = im.split()
    def scale(ch, s):
        w2, h2 = round(W * s), round(H * s); c = ch.resize((w2, h2), Image.BICUBIC)
        return c.crop(((w2 - W) // 2, (h2 - H) // 2, (w2 - W) // 2 + W, (h2 - H) // 2 + H))
    a = np.dstack([np.asarray(scale(r, 1.0030)), np.asarray(scale(g, 1.0015)), np.asarray(b)]).astype(np.float32) / 255
    a *= VIGN
    # film grain: soft, luma weighted
    rng = np.random.default_rng(500 + f)
    gr = Image.fromarray(np.clip(128 + rng.normal(0, 30, (H // 2, W // 2)), 0, 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    gn = (np.asarray(gr).astype(np.float32) - 128) / 128
    a += gn[..., None] * 0.022 * (0.5 + 0.5 * (1 - np.abs(a - 0.5) * 2))
    return a


def dust(a, f, strength):
    """Soft motes drifting in the sunlight (deterministic)."""
    if strength <= 0: return a
    rng = np.random.default_rng(42)
    n = 70; px = rng.uniform(0, W, n); py = rng.uniform(0, H, n); sz = rng.uniform(1.2, 4.5, n); sp = rng.uniform(0.2, 0.9, n)
    ph = rng.uniform(0, 6.28, n)
    lay = Image.new('L', (W, H), 0); d = ImageDraw.Draw(lay)
    for i in range(n):
        x = (px[i] + f * sp[i] * 0.9 + 14 * math.sin(f * 0.03 + ph[i])) % W
        y = (py[i] - f * sp[i] * 0.6 + 10 * math.cos(f * 0.025 + ph[i])) % H
        s = sz[i]; v = int(120 + 120 * (0.5 + 0.5 * math.sin(f * 0.08 + ph[i])))
        d.ellipse((x - s, y - s, x + s, y + s), fill=v)
    m = np.asarray(lay.filter(ImageFilter.GaussianBlur(1.6))).astype(np.float32)[..., None] / 255
    return a + m * strength * np.array([1.0, 0.92, 0.78])


def photo_frame(f):
    a = grade(load_render(f))
    img = Image.fromarray((a * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.6, percent=55, threshold=2))
    a = lens(img, f)
    if S2[0] <= f < S2[1]: a = dust(a, f, 0.10)
    if S5[0] <= f < S5[1]: a = dust(a, f, 0.07)
    if f < 5: a *= f / 5
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


# ---------------------------------------------------------------- redesigned end card
def logo_white(target_w=560):
    path = P('assets/logo_white.png')
    if os.path.exists(path):
        lg = Image.open(path).convert('RGBA'); return lg.resize((target_w, round(lg.height * target_w / lg.width)), Image.LANCZOS)
    big = Image.new('RGBA', (1400, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
    f1 = ImageFont.truetype(FONTB, 210); f2 = ImageFont.truetype(FONT, 92)
    for txt, fo, y in (('Nimble', f1, 20), ('Tech Solutions', f2, 290)):
        d.text(((1400 - d.textlength(txt, font=fo)) / 2, y), txt, font=fo, fill=(255, 255, 255, 255))
    d.rounded_rectangle((630, 262, 770, 276), 7, fill=APRICOT + (255,))
    big = big.crop(big.getbbox())
    return big.resize((target_w, round(big.height * target_w / big.width)), Image.LANCZOS)


_LOGO = None
LINES = [('tag', 'Websites and digital services', FONT, 44, WARM, 1040),
         ('wa', 'WhatsApp 068 178 9708', FONTB, 48, APRICOT, 1128),
         ('area', 'Midrand, Johannesburg, Remote', FONT, 38, MIST, 1212)]
HORIZON = 600; SUN_R = 130
_BG = None


def card_bg():
    global _BG
    if _BG is None:
        d = np.hypot((XX - CX) / 700, (YY - HORIZON) / 900)
        glow = np.clip(1 - d, 0, 1) ** 2
        base = np.array(TEAL, np.float32); lift = np.array((0x1E, 0x78, 0x82), np.float32)
        a = base + (lift - base) * glow[..., None]
        rng = np.random.default_rng(3); a += rng.normal(0, 1.6, (H, W, 1))
        _BG = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert('RGBA')
    return _BG.copy()


def end_card(f):
    global _LOGO
    if _LOGO is None: _LOGO = logo_white(540)
    img = card_bg()
    a0, a1 = END_ITEMS['arc']; t = clamp((f - a0) / (a1 - a0))
    e = 1 - (1 - t) ** 3
    # sun rising behind the horizon: glow + disc, clipped at the horizon line
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    cy = HORIZON + SUN_R * 1.05 - (SUN_R * 1.05 + 10) * e
    for k, al in ((2.3, 26), (1.7, 40), (1.3, 60)):
        r = SUN_R * k; d.ellipse((CX - r, cy - r, CX + r, cy + r), fill=APRICOT + (int(al * smooth(t * 2)),))
    lay = lay.filter(ImageFilter.GaussianBlur(26))
    d = ImageDraw.Draw(lay); d.ellipse((CX - SUN_R, cy - SUN_R, CX + SUN_R, cy + SUN_R), fill=APRICOT + (int(255 * smooth(t * 3)),))
    mask = Image.new('L', (W, H), 0); ImageDraw.Draw(mask).rectangle((0, 0, W, HORIZON), fill=255)
    lay.putalpha(Image.fromarray(np.minimum(np.asarray(lay.getchannel('A')), np.asarray(mask))))
    img.alpha_composite(lay)
    # horizon line draws out from the centre
    hl = smooth((f - a0) / 12); half = (SAFE['x1'] - SAFE['x0']) / 2 * hl
    if half > 1:
        ImageDraw.Draw(img).rounded_rectangle((CX - half, HORIZON, CX + half, HORIZON + 5), 2, fill=WARM + (255,))
    l0, l1 = END_ITEMS['logo']; ta = smooth((f - l0) / (l1 - l0))
    if ta > 0:
        lg = _LOGO.copy(); lg.putalpha(lg.getchannel('A').point(lambda v: int(v * ta)))
        img.alpha_composite(lg, (CX - lg.width // 2, 822 - lg.height // 2 + round(16 * (1 - ta))))
    for k, txt, font, size, col, y in LINES:
        b0, b1 = END_ITEMS[k]; tb = smooth((f - b0) / (b1 - b0))
        if tb <= 0: continue
        fo = ImageFont.truetype(font, size); tl = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dd = ImageDraw.Draw(tl)
        dd.text((CX - dd.textlength(txt, font=fo) / 2, y + round(12 * (1 - tb))), txt, font=fo, fill=col + (int(255 * tb),))
        img.alpha_composite(tl)
    return img.convert('RGB')


def end_layout():
    lg = logo_white(540); out = {'logo': (CX - lg.width / 2, 822 - lg.height / 2, CX + lg.width / 2, 822 + lg.height / 2),
                                 'sun_and_horizon': (SAFE['x0'], HORIZON - SUN_R * 1.0, SAFE['x1'], HORIZON + 5)}
    d = ImageDraw.Draw(Image.new('RGB', (4, 4)))
    for k, txt, font, size, col, y in LINES:
        fo = ImageFont.truetype(font, size); bb = d.textbbox((0, 0), txt, font=fo); tw = d.textlength(txt, font=fo)
        out[k] = (CX - tw / 2, y + bb[1], CX + tw / 2, y + bb[3])
    return out


def frame(f):
    if f < END: return photo_frame(f)
    card = end_card(f); x = smooth((f - END) / 12)
    if x >= 1: return card
    return Image.blend(photo_frame(min(f, S5[1] - 1)), card, x)


def work(fs):
    for f in fs: frame(f).save(P('build/frames', 'f%04d.png' % f), compress_level=1)
    return len(fs)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--frames'); ap.add_argument('-j', type=int, default=2)
    a = ap.parse_args(); os.makedirs(P('build/frames'), exist_ok=True)
    fs = [int(x) for x in a.frames.split(',')] if a.frames else list(range(N))
    from multiprocessing import Pool
    k = max(1, math.ceil(len(fs) / a.j))
    with Pool(a.j) as p: print(sum(p.map(work, [fs[i:i + k] for i in range(0, len(fs), k)])), 'frames')
