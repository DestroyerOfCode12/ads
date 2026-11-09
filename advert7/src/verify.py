"""Verifies the finished deliverables. Prints a plain report."""
import json, os, re, subprocess, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from timeline import *
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
D = os.path.join(ROOT, 'deliverables')
SND = os.path.join(D, 'nimble_tech_solutions_advert7_found_first_sound.mp4')
SIL = os.path.join(D, 'nimble_tech_solutions_advert7_found_first_silent.mp4')
run = lambda *a: subprocess.run(a, capture_output=True, text=True)

print('== Streams')
for f in (SND, SIL):
    j = json.loads(run('ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-show_format', '-of', 'json', f).stdout)
    v = [s for s in j['streams'] if s['codec_type'] == 'video'][0]
    a = [s for s in j['streams'] if s['codec_type'] == 'audio']
    print(os.path.basename(f))
    print('  video %sx%s %s fps(r) %s, frames counted %s, video duration %s s, container duration %s s' % (
        v['width'], v['height'], v['codec_name'], v['r_frame_rate'], v['nb_read_frames'], v.get('duration'), j['format']['duration']))
    print('  audio streams: %d %s' % (len(a), ('%s %s Hz %s ch, duration %s s' % (a[0]['codec_name'], a[0]['sample_rate'], a[0]['channels'], a[0].get('duration'))) if a else ''))
    tags = dict(j['format'].get('tags', {}))
    for s in j['streams']: tags.update({('stream%d:' % s['index']) + k: v for k, v in s.get('tags', {}).items()})
    print('  metadata tags left:', tags or 'none')

print('\n== Loudness and true peak measured on the finished MP4 audio track')
r = run('ffmpeg', '-hide_banner', '-nostats', '-i', SND, '-map', '0:a', '-af', 'ebur128=peak=true', '-f', 'null', '-')
txt = r.stderr[r.stderr.rfind('Summary'):]
I = re.search(r'I:\s+(-?[\d.]+) LUFS', txt).group(1); TP = re.search(r'Peak:\s+(-?[\d.]+) dBFS', txt).group(1)
LRA = re.search(r'LRA:\s+(-?[\d.]+) LU', txt).group(1)
print('  integrated %s LUFS, true peak %s dBTP, LRA %s LU' % (I, TP, LRA))

print('\n== Sound to picture (onsets found in the decoded MP4 audio vs. the frame each sound is cued to)')
tmp = os.path.join(ROOT, 'build', 'decoded.wav')
run('ffmpeg', '-y', '-hide_banner', '-i', SND, '-map', '0:a', '-ac', '1', '-ar', '48000', '-c:a', 'pcm_s16le', tmp)
with wave.open(tmp) as w: x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32)
print('  decoded audio samples %d (%.4f s)' % (len(x), len(x) / 48000))
X = np.fft.rfft(x); fq = np.fft.rfftfreq(len(x), 1 / 48000); X[fq < 1500] = 0
hp = np.abs(np.fft.irfft(X, len(x)))
env = np.convolve(hp, np.ones(96) / 96, 'same')
for name, f in [('key 1', key_frames()[0]), ('key 9', key_frames()[8]), ('key 18', key_frames()[-1]), ('enter', T_ENTER), ('trackpad click', T_CLICK)]:
    c = int(f / FPS * 48000); lo, hi = c - 2400, c + 2400
    seg = env[lo:hi]; thr = seg.max() * 0.5
    on = lo + np.argmax(seg > thr)
    print('  %-15s cue frame %3d (%.3f s)  onset %.3f s  offset %+.0f ms' % (name, f, f / FPS, on / 48000, (on - c) / 48))

print('\n== Tool names / provenance strings left in files')
# case sensitive, at least 4 characters, so random compressed bytes do not give false hits
pat = re.compile(rb'(x264|Lavf|Lavc|ffmpeg|FFmpeg|ElevenLabs|Eleven Labs|c2pa|jumbf|Playwright|HeadlessChrome|Chromium|Python|Pillow|numpy|Claude|Anthropic|FLUX|Black Forest|Inter Display|Adobe|xmpmeta|libx264)')
for f in sorted(os.listdir(D)):
    p = os.path.join(D, f)
    if os.path.isdir(p) or f.endswith(('.md', '.txt')): continue
    hits = sorted(set(m.group(0).decode('latin1') for m in pat.finditer(open(p, 'rb').read())))
    print('  %-55s %s' % (f, hits or 'none found'))
