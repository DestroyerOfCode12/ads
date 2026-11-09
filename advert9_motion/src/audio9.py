"""Original score and sound design for the motion graphics advert, synthesised in numpy (no samples).
120 bpm: one beat = 15 frames, so cuts on multiples of 15 land on the beat. Writes build/mix_raw.wav."""
import os, wave
import numpy as np
SR, FPS, N = 48000, 30, 450
L = N * SR // FPS
t = np.arange(L) / SR
rng = np.random.default_rng(9)
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
fr = lambda f: int(round(f * SR / FPS))
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
music = np.zeros((L, 2)); fx = np.zeros((L, 2))
BEAT = 0.5; END0 = 384 / FPS


def filt(x, lo=None, hi=None, o=2):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(f)
    if lo: g /= np.sqrt(1 + (lo / np.maximum(f, 1)) ** (2 * o))
    if hi: g /= np.sqrt(1 + (f / hi) ** (2 * o))
    return np.fft.irfft(X * g, len(x))


def put(buf, sig, s, g=1.0, pan=0.0):
    s = int(s); e = min(L, s + len(sig))
    if s >= L: return
    sig = sig[:e - s] * g
    buf[s:e, 0] += sig * np.sqrt(0.5 * (1 - pan)); buf[s:e, 1] += sig * np.sqrt(0.5 * (1 + pan))


def env(n, a, d):
    x = np.arange(n) / SR; return (1 - np.exp(-x / a)) * np.exp(-x / d)


# ---------------------------------------------------------------- music
chords = [(50, [62, 66, 69]), (47, [62, 66, 71]), (43, [62, 67, 71]), (45, [61, 64, 69])]
kick = np.zeros(L); clap = np.zeros(L); hat = np.zeros(L); bass = np.zeros(L); stab = np.zeros((L, 2)); pad = np.zeros((L, 2))
nb = int(15 / BEAT)
drop = (352 / FPS, END0)            # drums drop out under the riser
for b in range(nb + 1):
    st = b * BEAT
    if st >= END0 + 0.01: break
    inbreak = drop[0] <= st < drop[1]
    root, tones = chords[(b // 4) % 4]
    s = int(st * SR)
    if not inbreak:
        n = int(0.32 * SR); x = np.arange(n) / SR
        k = np.sin(2 * np.pi * np.cumsum(46 + 90 * np.exp(-x * 40)) / SR) * np.exp(-x * 9) * (1 - np.exp(-x * 700))
        e = min(L, s + n); kick[s:e] += k[:e - s]
        if b % 2 == 1:
            n = int(0.2 * SR); c = filt(rng.normal(0, 1, n), 900, 6000) * env(n, 0.001, 0.05)
            e = min(L, s + n); clap[s:e] += c[:e - s]
        for h in (0, 0.5):
            hs = int((st + h * BEAT) * SR); n = int(0.05 * SR); hh = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * 80)
            e = min(L, hs + n); hat[hs:e] += hh[:e - hs] * (0.6 if h == 0 else 1.0)
        # offbeat bass
        bs = int((st + 0.5 * BEAT) * SR); n = int(0.24 * SR); x = np.arange(n) / SR
        v = (np.sin(2 * np.pi * hz(root - 12) * x) + 0.5 * np.sign(np.sin(2 * np.pi * hz(root - 12) * x)) * 0.3) * env(n, 0.003, 0.12)
        e = min(L, bs + n); bass[bs:e] += v[:e - bs]
    # chord stab on the first beat of each bar, pad throughout
    if b % 4 == 0:
        n = int(2.0 * SR); x = np.arange(n) / SR
        for m in tones:
            for ch, det in ((0, -0.07), (1, 0.07)):
                v = sum(np.sin(2 * np.pi * hz(m + det) * hh * x) / hh ** 1.7 for hh in (1, 2, 3, 4))
                e = min(L, s + n); pad[s:e, ch] += (v * np.minimum(1, x / 0.08) * np.exp(-x * 0.5))[:e - s] * 0.12
                st_n = int(0.3 * SR); e2 = min(L, s + st_n)
                stab[s:e2, ch] += (v[:st_n] * env(st_n, 0.002, 0.09))[:e2 - s] * 0.22
hat = filt(hat, lo=7500); bass = filt(bass, hi=2200)
for ch in range(2):
    music[:, ch] += kick * 0.30 + clap * 0.07 + hat * 0.035 + bass * 0.16
music += pad + stab
# riser into the end card: filtered noise sweep plus rising tone
a, b = fr(352), fr(384); n = b - a; x = np.arange(n) / SR
sweep = filt(rng.normal(0, 1, n), 300, 9000) * np.linspace(0, 1, n) ** 2
tone = np.sin(2 * np.pi * np.cumsum(np.linspace(220, 880, n)) / SR) * np.linspace(0, 1, n) ** 3
put(music, sweep * 0.10 + tone * 0.05, a)
# final chord on the end card
n = L - fr(384); x = np.arange(n) / SR
fin = sum(np.sin(2 * np.pi * hz(m) * x) * (1 if m < 60 else 0.6) for m in (38, 50, 57, 62, 66, 69, 74))
put(music, fin * np.minimum(1, x / 0.01) * np.exp(-x * 0.9) * 0.05, fr(384))
# music fades gently over the last second
music *= np.clip((15.0 - t) / 1.0, 0, 1)[:, None] ** 1.2

# ---------------------------------------------------------------- sound design (under the music)
def slam(g=1.0):
    n = int(0.25 * SR); x = np.arange(n) / SR
    return (np.sin(2 * np.pi * np.cumsum(70 + 120 * np.exp(-x * 50)) / SR) * np.exp(-x * 14) + filt(rng.normal(0, 1, n), 1500, 8000) * np.exp(-x * 60) * 0.5) * g
def whoosh(dur, lo=300, hi=5000):
    n = fr(dur * FPS); x = np.linspace(0, 1, n); return filt(rng.normal(0, 1, n), lo, hi) * np.sin(np.pi * x) ** 2
def tick(g=1.0):
    n = int(0.03 * SR); return filt(rng.normal(0, 1, n), 2500, 10000) * np.exp(-np.arange(n) / SR * 200) * g
def blip(m, d=0.12):
    n = int(d * SR); x = np.arange(n) / SR; return np.sin(2 * np.pi * hz(m) * x) * env(n, 0.002, d / 3)
for f in (4, 10, 16): put(fx, slam(), fr(f), 0.20)
put(fx, whoosh(14, 200, 3000), fr(38), 0.10)
put(fx, slam(1.3), fr(48), 0.12)
for f in (60, 64, 88, 93): put(fx, whoosh(5, 800, 7000), fr(f), 0.06)
for i in range(0, 21, 2): put(fx, tick(0.7), fr(70 + i * 0.75), 0.10, 0.2)
put(fx, blip(86), fr(90), 0.05)
put(fx, whoosh(16, 300, 4000), fr(104), 0.07); put(fx, whoosh(14, 600, 8000), fr(120), 0.09)
for i in range(5): put(fx, slam(0.8), fr(135 + i * 30), 0.12)                      # service cuts, on the beat
for i in range(3): put(fx, whoosh(5, 1000, 8000), fr(137 + i * 2), 0.05, (i - 1) * 0.4)   # pages fan out
for i in range(4): put(fx, whoosh(4, 900, 7000), fr(167 + i * 3), 0.06, 0.3); put(fx, blip(88, 0.08), fr(175 + i * 3), 0.03)
for i in range(6): put(fx, blip(81 + (i % 3) * 2, 0.06), fr(205 + i * 3), 0.025, -0.3)
put(fx, whoosh(16, 2000, 9000), fr(203), 0.04)
for i in range(0, 18, 2): put(fx, tick(0.6), fr(226 + i * 0.67), 0.08)
n = int(0.4 * SR); x = np.arange(n) / SR
put(fx, np.sin(2 * np.pi * np.cumsum(60 + 80 * np.exp(-x * 30)) / SR) * np.exp(-x * 10), fr(237), 0.11)  # pin drop
put(fx, blip(79, 0.3), fr(241), 0.025)
put(fx, tick(1.2), fr(265), 0.12); put(fx, whoosh(20, 400, 3000), fr(270), 0.03)
put(fx, whoosh(10, 200, 3000), fr(284), 0.09)
for i in range(5): put(fx, slam(0.7), fr(290 + i * 12), 0.10)
put(fx, slam(1.6), fr(384), 0.16)
for f in (392, 398, 404): put(fx, tick(0.8), fr(f), 0.07)

mix = music + fx
mix /= np.abs(mix).max() / 0.5
from numpy.lib.stride_tricks import sliding_window_view
thr = 10 ** (-11.0 / 20); win = int(0.01 * SR)
e_ = np.abs(mix).max(1); e_ = sliding_window_view(np.pad(e_, (win // 2, win - win // 2 - 1), mode='edge'), win).max(1)
g = np.minimum(1, thr / np.maximum(e_, 1e-9)); gs = np.empty_like(g); acc = 1.0; rel = np.exp(-1 / (0.08 * SR))
for i in range(len(g)):
    acc = g[i] if g[i] < acc else rel * acc + (1 - rel) * g[i]; gs[i] = acc
mix *= gs[:, None]; mix *= np.clip(t / 0.005, 0, 1)[:, None]
os.makedirs(os.path.join(R, 'build'), exist_ok=True)
with wave.open(os.path.join(R, 'build/mix_raw.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())
sc = 0.5 / np.abs(music + fx).max()
def rms(v): return 20 * np.log10(np.sqrt(np.mean(v ** 2)) + 1e-12)
print('samples', L, '(%.3f s) | limiter max reduction %.1f dB' % (L / SR, -20 * np.log10(gs.min())))
for name, f in (('word slam', 4), ('wipe hit', 48), ('service cut', 165), ('pin drop', 237), ('end hit', 384)):
    sl = slice(fr(f), fr(f) + int(0.06 * SR)); print('%-11s fx %.1f dB  music %.1f dB' % (name, rms(fx[sl] * sc), rms(music[sl] * sc)))
