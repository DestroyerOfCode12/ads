# Advert 7, Found first: how it is built

Toolkit (different from adverts 1 to 6 on purpose):

| Step | Tool |
| --- | --- |
| Photoreal plates (desk wide 3072x5456, trackpad close up 1536x2736) | FLUX 3 Image, run through the ElevenLabs creative API. Originals with their C2PA records are in `assets/` |
| Screen UI (search page, results, website, mobile site) | Hand written HTML/CSS (`src/screen.html`, `src/phone.html`), rendered by headless Chromium through Playwright |
| Green screen key, homography, virtual camera, depth of field, grain, end card | Python, NumPy and Pillow (`src/composite.py`) |
| Score and sound effects | NumPy synthesis, no samples (`src/audio.py`) |
| Loudness, encode | ffmpeg: two pass linear loudnorm (`src/loudnorm.py`), libx264 and AAC (`src/encode.sh`) |

## Rebuild

```
python3 src/detect.py          # optional: re-measure the green screen corners
python3 src/make_states.py     # timeline -> unique UI states
NODE_PATH=$(npm root -g) node src/render_ui.js
python3 src/composite.py -j 4  # 480 PNG frames -> build/frames
python3 src/audio.py && python3 src/loudnorm.py
src/encode.sh
python3 src/check_safe.py && python3 src/verify.py
```

All timing lives in `src/timeline.py`. Camera framings live in `KF` and `TRACK` in
`src/composite.py`; close ups are defined by which UI span should fill the safe zone,
so text stays inside x 96 to 904 when it is readable.

## Swapping in the approved logo

The repository did not contain the approved stacked logo file, so the end card uses a
typographic stand in (Nimble over Tech Solutions in DejaVu Sans, white, with an apricot
rule). Put the approved white lockup at `assets/logo_white.png` (transparent PNG) and
rerun `composite.py` (frames 400 to 479 are enough: `--frames 400,401,...`) and
`encode.sh`. The site mockup also shows a text wordmark in its nav strip.
