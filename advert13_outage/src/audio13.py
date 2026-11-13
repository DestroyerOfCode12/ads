"""Score, sound design and voiceover mix for 'Still Online' (20 s, 600 frames at 30 fps).
Music and effects are synthesised in numpy; the voiceover is the ElevenLabs take in assets/vo.
Writes build/mix_raw.wav (with voiceover) and build/mix_raw_novo.wav (music and effects only)."""
import os, subprocess, wave
import numpy as np
SR, FPS, N = 48000, 30, 600
L = N * SR // FPS
t = np.arange(L) / SR
rng = np.random.default_rng(13)
R = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
fr = lambda f: int(round(f * SR / FPS))
hz = lambda m: 440 * 2 ** ((m - 69) / 12)
music = np.zeros((L, 2)); fx = np.zeros((L, 2)); vo = np.zeros(L)

def filt(x, lo=None, hi=None, o=2):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(f)
    if lo: g /= np.sqrt(1 + (lo / np.maximum(f, 1)) ** (2 * o))
    if hi: g /= np.sqrt(1 + (f / hi) ** (2 * o))
    return np.fft.irfft(X * g, len(x))
def put(buf, sig, s, g=1.0, pan=0.0):
    s = int(s); e = min(L, s + len(sig))
    if s >= L: return
    sig = sig[:e - s] * g
    if buf.ndim == 1: buf[s:e] += sig; return
    buf[s:e, 0] += sig * np.sqrt(0.5 * (1 - pan)); buf[s:e, 1] += sig * np.sqrt(0.5 * (1 + pan))
def env(n, a, d): x = np.arange(n) / SR; return (1 - np.exp(-x / a)) * np.exp(-x / d)
def blip(m, d=0.15): n = int(d * SR); x = np.arange(n) / SR; return (np.sin(2 * np.pi * hz(m) * x) + 0.25 * np.sin(4 * np.pi * hz(m) * x)) * env(n, 0.002, d / 3)
def tick(g=1.0): n = int(0.03 * SR); return filt(rng.normal(0, 1, n), 2500, 10000) * np.exp(-np.arange(n) / SR * 200) * g
def whoosh(frames, lo=300, hi=5000): n = fr(frames); x = np.linspace(0, 1, n); return filt(rng.normal(0, 1, n), lo, hi) * np.sin(np.pi * x) ** 2
def pad(notes, a, b, gain, bright=4):
    n = fr(b) - fr(a); x = np.arange(n) / SR; e = np.minimum(1, x / 0.6) * np.minimum(1, (x[-1] - x) / 0.6); out = np.zeros((n, 2))
    for m in notes:
        for ch, det in ((0, -0.07), (1, 0.07)):
            out[:, ch] += sum(np.sin(2 * np.pi * hz(m + det) * h * x + h) / h ** 1.8 for h in range(1, bright + 1)) * e
    s = fr(a); music[s:s + n] += out[:L - s] * gain

# ---------- shot 1 (0 to 5 s): tense, muted. low drone, a ticking clock, the refresher's clicks
pad([38, 45, 50, 53], 0, 160, 0.10, bright=2)                          # D minor, dark
drone = filt(rng.normal(0, 1, fr(160)), 40, 180) * 0.6
put(music, drone * np.minimum(1, np.arange(fr(160)) / SR / 0.5) * np.minimum(1, (fr(160) - np.arange(fr(160))) / SR / 0.6), 0, 0.10)
for k in range(10): put(fx, tick(0.6), fr(k * 15), 0.06)              # clock tick on every beat
f = 75
while f < 150:                                                         # mouse clicks on each tap of the refresher
    put(fx, tick(1.0), fr(f), 0.08, 0.2); put(fx, blip(96, 0.02), fr(f), 0.03, 0.2); f += 2 * np.pi / 0.55
# ---------- shot 2 (5 to 10 s): warm bloom, phone ping, a contented sip, the reply
put(fx, whoosh(40, 200, 4000), fr(140), 0.05)                          # camera slides across the room
pad([50, 57, 62, 66, 69], 150, 310, 0.13)                              # D major, warm
put(fx, blip(84, 0.25) + 0.6 * blip(91, 0.25), fr(200), 0.11, 0.2)      # phone ping
for k in range(4): put(fx, tick(0.7), fr(282 + k * 5), 0.08)           # reply taps
# ---------- shot 3 (10 to 15 s): the groove, one satisfying chime per arriving email
BEAT = 0.5
for b in range(int((450 - 300) / 15) + 1):
    st = 300 / FPS + b * BEAT; s = int(st * SR); n = int(0.3 * SR); x = np.arange(n) / SR
    k = np.sin(2 * np.pi * np.cumsum(46 + 90 * np.exp(-x * 40)) / SR) * np.exp(-x * 9) * (1 - np.exp(-x * 700))
    put(music, k, s, 0.28)
    hh = filt(rng.normal(0, 1, int(0.05 * SR)), 7000) * np.exp(-np.arange(int(0.05 * SR)) / SR * 80)
    put(music, hh, int((st + BEAT / 2) * SR), 0.05)
    bass_n = int(0.24 * SR); bx = np.arange(bass_n) / SR
    put(music, np.sin(2 * np.pi * hz(38 if (b // 4) % 2 == 0 else 43) * bx) * env(bass_n, 0.003, 0.12), int((st + BEAT / 2) * SR), 0.16)
pad([50, 57, 62, 66, 69], 300, 380, 0.09); pad([47, 54, 62, 66, 71], 380, 455, 0.09)
for i, m in enumerate([81, 83, 86, 88, 90, 93]):                       # emails arriving (MAIL0 + i * MAILSTEP)
    put(fx, blip(m, 0.22) + 0.4 * blip(m + 7, 0.22), fr(312 + i * 17), 0.10, 0.25)
put(fx, whoosh(10, 600, 8000), fr(298), 0.05)
# ---------- shot 4 (15 to 20 s): resolve, logo, the call to action
n = L - fr(450); x = np.arange(n) / SR
put(music, sum(np.sin(2 * np.pi * hz(m) * x) * (1 if m < 60 else .6) for m in (38, 50, 57, 62, 66, 69, 74)) * np.minimum(1, x / .01) * np.exp(-x * .55), fr(450), 0.045)
put(fx, blip(86, 0.5) + 0.5 * blip(93, 0.5), fr(460), 0.04)
put(fx, blip(88, 0.18) + 0.5 * blip(95, 0.18), fr(492), 0.08)            # button lands
music *= np.clip((20.0 - t) / 1.4, 0, 1)[:, None] ** 1.2

# ---------- voiceover: four phrases from the take, placed on their moments
vo_mp3 = os.path.join(R, 'assets/vo/vo_full.mp3'); vo_wav = os.path.join(R, 'build/vo48k.wav')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', vo_mp3, '-ac', '1', '-ar', str(SR), vo_wav], check=True)
with wave.open(vo_wav) as w: v = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float64) / 32768
PHRASES = [((0.00, 1.70), 2.55), ((2.25, 3.22), 9.05), ((3.80, 7.78), 10.55), ((8.10, 9.33), 16.6)]   # (source span s, place at s)
for (a, b), at in PHRASES:
    seg_ = v[int(a * SR):int(b * SR)].copy(); fade = int(0.02 * SR)
    seg_[:fade] *= np.linspace(0, 1, fade); seg_[-fade:] *= np.linspace(1, 0, fade)
    put(vo, seg_, int(at * SR))
vo = filt(vo, lo=90)                                                  # tidy the low end
# duck music (and lightly the effects) under the voice
venv = np.convolve(np.abs(vo), np.ones(int(0.05 * SR)) / int(0.05 * SR), 'same')
duck = 1 - 0.72 * np.clip(venv / (venv.max() * 0.25 + 1e-9), 0, 1)
duck = np.convolve(duck, np.ones(int(0.12 * SR)) / int(0.12 * SR), 'same')

def master(with_vo):
    m = music * (duck[:, None] if with_vo else 1) + fx * ((0.8 + 0.2 * duck[:, None]) if with_vo else 1)
    if with_vo: m = m + np.stack([vo, vo], 1) * 2.4
    m /= np.abs(m).max() / 0.5
    from numpy.lib.stride_tricks import sliding_window_view
    thr = 10 ** (-13.5 / 20); win = int(0.01 * SR)
    e_ = np.abs(m).max(1); e_ = sliding_window_view(np.pad(e_, (win // 2, win - win // 2 - 1), mode='edge'), win).max(1)
    g = np.minimum(1, thr / np.maximum(e_, 1e-9)); gs = np.empty_like(g); acc = 1.0; rel = np.exp(-1 / (0.08 * SR))
    for i in range(len(g)): acc = g[i] if g[i] < acc else rel * acc + (1 - rel) * g[i]; gs[i] = acc
    m *= gs[:, None]; m *= np.clip(t / 0.005, 0, 1)[:, None]
    return m, gs
for name, wv in (('mix_raw.wav', True), ('mix_raw_novo.wav', False)):
    m, gs = master(wv)
    with wave.open(os.path.join(R, 'build', name), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(m, -1, 1) * 32767).astype('<i2').tobytes())
    print(name, 'limiter max reduction %.1f dB' % (-20 * np.log10(gs.min())))
def rms(x): return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
for nm, (a, b) in (('VO phrase 1', (2.6, 4.0)), ('VO phrase 3', (10.8, 14.2))):
    sl = slice(int(a * SR), int(b * SR)); print('%-12s voice %.1f dB  music under it %.1f dB' % (nm, rms(vo[sl] * 2.4), rms((music * duck[:, None])[sl])))
