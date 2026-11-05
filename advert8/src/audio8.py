"""Original score and foley for advert 8 (Open all hours), synthesised in numpy (no samples, no voices).
Writes build/mix_raw.wav (48 kHz stereo, exactly 16.000 s)."""
import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from timing8 import *

SR = 48000; L = N * SR // FPS
t = np.arange(L) / SR
rng = np.random.default_rng(11)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
fr = lambda f: int(round(f * SR / FPS))
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
music = np.zeros((L, 2)); fx = np.zeros((L, 2))


def filt(x, lo=None, hi=None, order=2):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(f)
    if lo: g /= np.sqrt(1 + (lo / np.maximum(f, 1)) ** (2 * order))
    if hi: g /= np.sqrt(1 + (f / hi) ** (2 * order))
    return np.fft.irfft(X * g, len(x))


def put(buf, sig, start, gain=1.0, pan=0.0):
    s = int(start); e = min(L, s + len(sig)); sig = sig[:e - s] * gain
    buf[s:e, 0] += sig * np.sqrt(0.5 * (1 - pan)); buf[s:e, 1] += sig * np.sqrt(0.5 * (1 + pan))


def env(n, a=0.002, d=0.2):
    tt = np.arange(n) / SR; return (1 - np.exp(-tt / a)) * np.exp(-tt / d)


# ---------------------------------------------------------------- music, 104 bpm, D major, warm and bright
BPM = 104; beat = 60 / BPM; s16 = beat / 4
bars = [  # chord per bar (root midi, triad/7th tones)
    (50, [62, 66, 69, 73]), (47, [62, 66, 69, 71]), (43, [59, 62, 66, 69]), (45, [61, 64, 69, 71]),
    (50, [62, 66, 69, 73]), (47, [62, 66, 69, 71]), (43, [59, 62, 67, 71]), (50, [62, 66, 69, 76]),
]
OPEN = 0.0
NIGHT0 = SHUTTER_DOWN[1] / FPS; DAWN = SHUTTER_UP[0] / FPS
END_T = END / FPS
nbars = int(16 / (4 * beat)) + 1
pluck_buf = np.zeros(L); bass_buf = np.zeros(L); pad_buf = np.zeros((L, 2)); kick = np.zeros(L); hat = np.zeros(L)
for b in range(nbars):
    root, tones = bars[b % len(bars)] if b * 4 * beat < END_T else (50, [62, 66, 69, 74])
    t0 = b * 4 * beat
    # pad: soft detuned sines, whole bar
    n = int(4 * beat * SR) + int(0.4 * SR); tt = np.arange(n) / SR
    pe = np.minimum(1, tt / 0.25) * np.minimum(1, np.maximum(0, (4 * beat + 0.4 - tt) / 0.4))
    for m in tones:
        for ch, det in ((0, -0.08), (1, 0.08)):
            v = sum(np.sin(2 * np.pi * hz(m + det) * h * tt + rng.uniform(0, 6)) / h ** 1.8 for h in (1, 2, 3))
            s = int(t0 * SR); e = min(L, s + n); pad_buf[s:e, ch] += (v * pe)[:e - s] * 0.16
    # plucked arpeggio, 16ths, pattern through chord tones
    pat = [0, 2, 1, 3, 2, 1, 3, 2, 0, 2, 1, 3, 2, 3, 1, 2]
    for i, k in enumerate(pat):
        st = t0 + i * s16
        if st >= 16: break
        if i % 4 == 3 and rng.random() < 0.35: continue
        m = tones[k] + (12 if i in (6, 14) else 0)
        n = int(0.35 * SR); tt = np.arange(n) / SR
        f0 = hz(m)
        v = (np.sin(2 * np.pi * f0 * tt) + 0.35 * np.sin(2 * np.pi * 2 * f0 * tt) * np.exp(-tt * 18) + 0.12 * np.sin(2 * np.pi * 3.01 * f0 * tt) * np.exp(-tt * 30))
        v *= env(n, 0.001, 0.12) * (0.9 if i % 4 == 0 else 0.6)
        s = int(st * SR); e = min(L, s + n); pluck_buf[s:e] += v[:e - s]
    # bass: root on beats 1 and 3, octave on the "and" of 4
    for bt, m in ((0, root - 12), (2, root - 12), (3.5, root)):
        st = t0 + bt * beat; n = int(0.5 * SR); tt = np.arange(n) / SR
        v = np.sin(2 * np.pi * hz(m) * tt) + 0.3 * np.sin(2 * np.pi * 2 * hz(m) * tt)
        v *= env(n, 0.004, 0.28)
        s = int(st * SR); e = min(L, s + n)
        if s < L: bass_buf[s:e] += v[:e - s]
    # drums
    for bt in range(4):
        st = t0 + bt * beat; s = int(st * SR)
        if s >= L: break
        n = int(0.3 * SR); tt = np.arange(n) / SR
        f = 48 + 70 * np.exp(-tt * 35); k = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9) * (1 - np.exp(-tt * 600))
        e = min(L, s + n); kick[s:e] += k[:e - s]
    for i in range(8):
        st = t0 + (i + 0.5) * beat / 2 * 1.0; s = int(st * SR)
        if s >= L: break
        n = int(0.06 * SR); h = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * 70)
        e = min(L, s + n); hat[s:e] += h[:e - s] * (1.0 if i % 2 else 0.6)
hat = filt(hat, lo=7000)

# arrangement: before the lights only a filtered pad and pluck; drums and bass enter when the lights come on
gate = np.clip((NIGHT0 - t) / 0.8, 0, 1) + np.clip((t - DAWN) / 0.3, 0, 1)
gate = np.clip(gate, 0, 1)
pre = 1 - gate
# simple swept low-pass on the pluck before OPEN: blend a heavily filtered copy
pl_dark = filt(pluck_buf, hi=900)
pluck = pl_dark * pre + pluck_buf * gate
endfade = np.clip((16 - t) / 1.2, 0, 1) ** 1.3
drums_gate = gate * np.clip((END_T + 1.6 - t) / 0.4, 0, 1)
# night: sparse bell notes instead of the groove
bell = np.zeros(L)
for k, (tt0, m) in enumerate([(4.3, 81), (5.1, 76), (5.9, 78), (6.9, 74), (7.6, 81), (8.3, 78)]):
    n = int(1.6 * SR); x = np.arange(n) / SR
    v = (np.sin(2*np.pi*hz(m)*x) + 0.3*np.sin(2*np.pi*hz(m)*2.76*x)*np.exp(-x*6)) * np.exp(-x*2.2) * (1-np.exp(-x*800))
    s0 = int(tt0*SR); e0 = min(L, s0+n); bell[s0:e0] += v[:e0-s0]
music[:, 0] += bell * 0.05; music[:, 1] += bell * 0.05
dip = 1 - 0.65 * np.clip((t - NIGHT0 + 0.5) / 1.0, 0, 1) * np.clip((DAWN - t) / 0.5, 0, 1)
pluck = pluck * dip; pad_buf = pad_buf * dip[:, None]
for ch, pan in ((0, -0.25), (1, 0.25)):
    music[:, ch] += pluck * 0.11 * np.sqrt(0.5 * (1 - pan * (1 if ch == 0 else -1)))
music += pad_buf * 0.5
music[:, 0] += bass_buf * 0.13 * gate; music[:, 1] += bass_buf * 0.13 * gate
music[:, 0] += kick * 0.22 * drums_gate; music[:, 1] += kick * 0.22 * drums_gate
music[:, 0] += hat * 0.02 * drums_gate; music[:, 1] += hat * 0.026 * drums_gate
# intro: music fades in over the first second
music *= np.clip(t / 1.0, 0, 1)[:, None] * 0.75 + 0.25 * np.clip(t / 0.3, 0, 1)[:, None]
music *= endfade[:, None]

# ---------------------------------------------------------------- foley (kept under the music)
def shutter_sfx(a, b, pan):
    n = fr(b) - fr(a); tt = np.arange(n) / SR
    rate = 18 + 10 * np.sin(np.pi * np.clip(tt / tt[-1], 0, 1))
    ph = np.cumsum(rate) / SR; clicks = (np.sin(2 * np.pi * ph) > 0.92).astype(float)
    r = filt(rng.normal(0, 1, n), 700, 4200) * (0.35 + clicks * 1.2)
    r *= np.minimum(1, tt / 0.15) * np.minimum(1, (tt[-1] - tt) / 0.1)
    put(fx, r, fr(a), 0.3, pan)
    nn = int(0.25 * SR); t2 = np.arange(nn) / SR
    put(fx, np.sin(2*np.pi*90*t2)*np.exp(-t2*22) + filt(rng.normal(0,1,nn),300,2500)*np.exp(-t2*40)*0.6, fr(b), 0.22)
shutter_sfx(*SHUTTER_DOWN, -0.1)
shutter_sfx(*SHUTTER_UP, 0.0)
def tick(f, g):
    nn = int(0.04 * SR); put(fx, filt(rng.normal(0, 1, nn), 1500, 8000) * np.exp(-np.arange(nn) / SR * 160), fr(f), 0.35 * g, 0.3)
for f, g in ((LAMP_ON + 1, 0.8), (LAMP_ON + 2, 0.4), (LAMP_ON + 4, 0.9), (LAMP_ON + 6, 0.6)): tick(f, g)
# street lamp hum while it is on (very low)
hum_n = fr(SUNRISE[0] + 20) - fr(LAMP_ON + 4); th = np.arange(hum_n) / SR
put(fx, (np.sin(2*np.pi*100*th) + 0.4*np.sin(2*np.pi*200*th)) * np.minimum(1, th/0.2), fr(LAMP_ON + 4), 0.006, 0.4)
tick(LIGHTS_OFF + 1, 1.0)
for f, g in ((LIGHTS_ON + 1, 1.0), (LIGHTS_ON + 2, 0.5), (LIGHTS_ON + 4, 0.8), (LIGHTS_ON + 7, 0.9)): tick(f, g)
# night ambience: synthesised crickets and far traffic, only while the shop is shut
night_env = np.clip((t - SHUTTER_DOWN[0] / FPS) / 1.0, 0, 1) * np.clip((SHUTTER_UP[0] / FPS + 0.6 - t) / 0.8, 0, 1)
cr = np.zeros(L)
for k in range(3):
    f0 = 4300 + 350 * k; rate = 2.6 + 0.7 * k; ph0 = rng.uniform(0, 1)
    gate_c = (np.sin(2 * np.pi * (t * rate + ph0)) > 0.55).astype(float)
    chirp = (np.sin(2 * np.pi * 38 * t) > 0).astype(float)
    cr += np.sin(2 * np.pi * f0 * t) * gate_c * chirp * (0.7 + 0.3 * np.sin(2*np.pi*0.3*t + k))
cr = filt(cr, 3000, 7000)
traffic = filt(rng.normal(0, 1, L), 60, 400) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.11 * t))
fx[:, 0] += (cr * 0.06 + traffic * 0.11) * night_env; fx[:, 1] += (cr * 0.05 + traffic * 0.11) * night_env
# phone buzz and the email tone
nn = fr(10); tt3 = np.arange(nn) / SR
buzz = np.sign(np.sin(2 * np.pi * 172 * tt3)) * (0.6 + 0.4 * np.sin(2 * np.pi * 31 * tt3))
put(fx, filt(buzz, 120, 1800) * np.minimum(1, tt3 / 0.01) * np.minimum(1, (tt3[-1] - tt3) / 0.02), fr(BUZZ), 0.12)
def chime(ms, dur=0.9, dec=5, gap=0.08):
    n = int(dur * SR); tt = np.arange(n) / SR; v = np.zeros(n)
    for jj, m in enumerate(ms):
        d = int(jj * gap * SR); x = tt[:n - d]
        v[d:] += (np.sin(2 * np.pi * hz(m) * x) + 0.2 * np.sin(2 * np.pi * 2 * hz(m) * x)) * np.exp(-x * dec) * (1 - np.exp(-x * 900))
    return v
put(fx, chime([79, 86]), fr(NOTE), 0.09, 0.15)
# sign flip
a, b = FLIP
nn = fr(9); put(fx, filt(rng.normal(0, 1, nn), 900, 6000) * np.sin(np.pi * np.arange(nn) / nn), fr(a), 0.14, 0.1)
nn = int(0.08 * SR); put(fx, filt(rng.normal(0, 1, nn), 2000, 9000) * np.exp(-np.arange(nn) / SR * 90), fr(a + 9), 0.3, 0.1)
for f in (S2A[0], S2B[0], S3[0], S4[0]):
    nn = fr(8); put(fx, filt(rng.normal(0, 1, nn), 300, 3000) * np.linspace(0, 1, nn) ** 2, fr(f) - nn, 0.012)
nn = int(2.5 * SR); tt4 = np.arange(nn) / SR
put(fx, sum(np.sin(2 * np.pi * hz(m) * tt4) for m in (38, 50, 57)) * np.exp(-tt4 * 1.6) * (1 - np.exp(-tt4 * 300)), fr(END + 2), 0.05)
put(fx, chime([74, 78, 81, 86], 2.2, 2.4, 0.07), fr(END_ITEMS['logo'][0]), 0.03)

mix = music + fx
mix /= np.abs(mix).max() / 0.5
# gentle peak limiter so linear loudnorm keeps true peak headroom
from numpy.lib.stride_tricks import sliding_window_view
thr = 10 ** (-11.0 / 20); win = int(0.01 * SR)
e_ = np.abs(mix).max(1); e_ = sliding_window_view(np.pad(e_, (win // 2, win - win // 2 - 1), mode='edge'), win).max(1)
g = np.minimum(1, thr / np.maximum(e_, 1e-9)); gs = np.empty_like(g); acc = 1.0; rel = np.exp(-1 / (0.08 * SR))
for i in range(len(g)):
    acc = g[i] if g[i] < acc else rel * acc + (1 - rel) * g[i]; gs[i] = acc
mix *= gs[:, None]
mix *= np.clip(t / 0.01, 0, 1)[:, None]
pcm = (np.clip(mix, -1, 1) * 32767).astype('<i2')
os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
with wave.open(os.path.join(ROOT, 'build/mix_raw.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
# UI/foley vs music check (60 ms RMS around each sound)
sc = 0.5 / np.abs(music + fx).max()
def rms(x): return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
print('samples', L, '| limiter max reduction %.1f dB' % (-20 * np.log10(gs.min())))
for name, f in [('shut dn', SHUTTER_DOWN[0] + 15), ('clunk', SHUTTER_DOWN[1]), ('lamp', LAMP_ON + 1), ('night', 150), ('buzz', BUZZ + 2), ('chime', NOTE), ('shut up', SHUTTER_UP[0] + 15), ('flip', FLIP[0] + 9), ('end hit', END + 2)]:
    sl = slice(fr(f), fr(f) + int(0.06 * SR))  # 60 ms
    print('%-8s foley %.1f dB   music %.1f dB' % (name, rms(fx[sl] * sc), rms(music[sl] * sc)))
