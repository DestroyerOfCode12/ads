"""Original score and UI sounds, synthesised in numpy (no samples). Writes build/mix_raw.wav."""
import os, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from timeline import *

SR = 48000
L = N * SR // FPS              # 768000 samples = 16.000 s
t = np.arange(L) / SR
rng = np.random.default_rng(7)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def fr(f): return int(round(f * SR / FPS))
def hz(m): return 440 * 2 ** ((m - 69) / 12)


def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR); y = np.empty_like(x); s = 0.0
    for i in range(len(x)): s = (1 - a) * x[i] + a * s; y[i] = s
    return y


def lp_fft(x, fc, order=2):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    return np.fft.irfft(X / np.sqrt(1 + (f / fc) ** (2 * order)), len(x))


def bp_fft(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    g = 1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 4) / np.sqrt(1 + (f / hi) ** 4)
    return np.fft.irfft(X * g, len(x))


mixL = np.zeros(L); mixR = np.zeros(L)


def add(sig, start, gain=1.0, pan=0.0):
    s = int(start)  # sample index
    e = min(L, s + len(sig)); sig = sig[:e - s] * gain
    mixL[s:e] += sig * np.sqrt(0.5 * (1 - pan))
    mixR[s:e] += sig * np.sqrt(0.5 * (1 + pan))


# ---------------------------------------------------------------- warm pad
CHORDS = [  # (start s, midi notes)
    (0.0, [50, 57, 62, 66, 73]),          # D maj7 (D A D F# C#)
    (T_RES / FPS, [47, 54, 62, 66, 69, 73]),  # B m9 colour
    (T_SITE / FPS, [43, 50, 59, 62, 66]),    # G maj7
    (T_END / FPS, [50, 57, 64, 66, 69]),     # D add9, resolves on the end card
]
pad = np.zeros((2, L))
for i, (st, notes) in enumerate(CHORDS):
    en = CHORDS[i + 1][0] if i + 1 < len(CHORDS) else 16.0
    env = np.clip((t - st) / 0.9, 0, 1) * np.clip((en + 0.6 - t) / 0.6, 0, 1)
    env = env ** 1.5
    for k, m in enumerate(notes):
        for ch, det in ((0, -0.06), (1, 0.06)):
            f0 = hz(m + det * (1 if k % 2 else -1))
            ph = rng.uniform(0, 2 * np.pi)
            v = np.zeros(L)
            for h in range(1, 7):          # soft saw: few harmonics, steep rolloff
                v += np.sin(2 * np.pi * f0 * h * t + ph * h) / h ** 1.6
            pad[ch] += v * env * (0.9 if m < 55 else 0.55)
# slow filter breathing
for ch in range(2):
    pad[ch] = lp_fft(pad[ch], 1400)
trem = 1 + 0.06 * np.sin(2 * np.pi * 0.21 * t)
pad *= trem
pad *= 0.045
mixL += pad[0]; mixR += pad[1]

# ---------------------------------------------------------------- soft low pulse (96 bpm)
beat = 60 / 96
pulse = np.zeros(L)
nb = int(16 / beat) + 1
for b in range(nb):
    st = b * beat
    if st > (T_END + 30) / FPS: break
    s = int(st * SR); n = int(0.42 * SR); tt = np.arange(n) / SR
    f = 46 + 22 * np.exp(-tt * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    acc = 1.0 if b % 4 == 0 else 0.7
    v = np.sin(ph) * np.exp(-tt * 7.5) * (1 - np.exp(-tt * 400)) * acc
    e = min(L, s + n); pulse[s:e] += v[:e - s]
# pulse enters gently after the opening second, sits under everything
pulse *= np.clip((t - 0.6) / 1.5, 0, 1) * 0.16
mixL += pulse; mixR += pulse

# ---------------------------------------------------------------- UI sounds (kept quiet)
def keystroke(strength=1.0):
    n = int(0.06 * SR); tt = np.arange(n) / SR
    noise = bp_fft(rng.normal(0, 1, n), 1800, 6500)
    click = noise * np.exp(-tt * 140) * (1 - np.exp(-tt * 3000))
    thock = np.sin(2 * np.pi * (170 + rng.uniform(-15, 15)) * tt) * np.exp(-tt * 90)
    return (click * 0.6 + thock * 0.5) * strength


for i, k in enumerate(key_frames()):
    add(keystroke(rng.uniform(0.75, 1.0)), int(fr(k) + rng.integers(-300, 300)), 0.13, pan=rng.uniform(-0.2, 0.2))
add(keystroke(1.3), fr(T_ENTER), 0.11)


def blip(f0, f1, dur=0.16):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f0 + (f1 - f0) * np.clip(tt / 0.05, 0, 1)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 22) * (1 - np.exp(-tt * 800))


add(blip(880, 1318), fr(T_PIN + 4), 0.045, pan=0.1)


def trackpad_click():
    n = int(0.05 * SR); tt = np.arange(n) / SR
    hi = bp_fft(rng.normal(0, 1, n), 3000, 9000) * np.exp(-tt * 260)
    lo = np.sin(2 * np.pi * 120 * tt) * np.exp(-tt * 120)
    return hi * 0.5 + lo * 0.6


add(trackpad_click(), fr(T_CLICK), 0.2)
# page load: a very soft airy swell
n = fr(16); sw = bp_fft(rng.normal(0, 1, n), 400, 3000)
envs = np.sin(np.pi * np.clip(np.arange(n) / n, 0, 1)) ** 2
add(sw * envs, fr(T_INS1 + 2), 0.012)


def chime(notes, dur=1.4, decay=3.5):
    n = int(dur * SR); tt = np.arange(n) / SR; v = np.zeros(n)
    for j, m in enumerate(notes):
        d = int(j * 0.09 * SR)
        a = np.sin(2 * np.pi * hz(m) * tt[:n - d]) + 0.25 * np.sin(2 * np.pi * hz(m) * 2.01 * tt[:n - d])
        v[d:] += a * np.exp(-tt[:n - d] * decay) * (1 - np.exp(-tt[:n - d] * 600))
    return v


add(chime([76, 81]), fr(T_PHONE), 0.03, pan=0.25)        # phone wakes
add(chime([62, 69, 74], 2.0, 2.2), fr(END_ITEMS['logo'][0]), 0.03)   # logo lands

# ---------------------------------------------------------------- master
mix = np.stack([mixL, mixR], 1)
fade_in = np.clip(t / 0.02, 0, 1); fade_out = np.clip((16.0 - t) / 0.7, 0, 1) ** 1.5
mix *= (fade_in * fade_out)[:, None]
mix /= np.abs(mix).max() / 0.5
# gentle peak limiter (10 ms lookahead window, smooth release) so loudness
# normalisation can stay linear and still leave true peak headroom
thr = 10 ** (-10.5 / 20)
env = np.abs(mix).max(1)
win = int(0.01 * SR)
from numpy.lib.stride_tricks import sliding_window_view
envp = np.pad(env, (win // 2, win - win // 2 - 1), mode='edge')
env = sliding_window_view(envp, win).max(1)
g = np.minimum(1, thr / np.maximum(env, 1e-9))
# smooth gain (fast attack is already handled by the lookahead max)
gs = np.empty_like(g); acc = 1.0; rel = np.exp(-1 / (0.08 * SR))
for i in range(len(g)):
    acc = g[i] if g[i] < acc else rel * acc + (1 - rel) * g[i]; gs[i] = acc
mix *= gs[:, None]
print('limiter max reduction %.1f dB' % (-20 * np.log10(gs.min())))
os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
pcm = (np.clip(mix, -1, 1) * 32767).astype('<i2')
with wave.open(os.path.join(ROOT, 'build/mix_raw.wav'), 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('samples', L, 'seconds', L / SR)

# report: UI sounds vs music bed (50 ms RMS around each UI event)
scale = 0.5 / np.abs(np.stack([mixL, mixR], 1) * (fade_in * fade_out)[:, None]).max()
bed = (np.stack([pad[0] + pulse, pad[1] + pulse], 1)) * (fade_in * fade_out)[:, None] * scale
ui = mix - bed
def rms(x): return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
w = int(0.06 * SR)
print('bed RMS over whole spot: %.1f dBFS, UI peak %.1f dBFS vs bed peak %.1f dBFS' % (rms(bed), 20*np.log10(np.abs(ui).max()), 20*np.log10(np.abs(bed).max())))
for name, f in [('keys', key_frames()[5]), ('enter', T_ENTER), ('pin', T_PIN + 4), ('click', T_CLICK), ('phone', T_PHONE), ('logo', END_ITEMS['logo'][0])]:
    s0 = fr(f); seg = slice(s0, s0 + w)
    print('%-6s UI %.1f dB  bed %.1f dB (60 ms RMS)   UI peak %.1f  bed peak %.1f' % (name, rms(ui[seg]), rms(bed[seg]), 20*np.log10(np.abs(ui[seg]).max()), 20*np.log10(np.abs(bed[seg]).max())))
