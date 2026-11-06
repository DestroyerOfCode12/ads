# Nimble Tech Solutions advert 7, Found first: reusable prompt

Build a 16 second vertical advert (1080 by 1920, 30 fps, 480 frames, MP4, plus a
copy with no audio stream) for Nimble Tech Solutions, owner run web and IT
business in Midrand, Gauteng. Photoreal, not flat vector: this advert breaks
from adverts 1 to 6 on purpose.

PLATES (image generation, FLUX 3 Image via ElevenLabs, 9:16)
1. Desk wide, 4K: over the shoulder from behind an anonymous person (no face),
   silver laptop on a light oak desk, laptop display and a phone lying flat
   both showing flat chroma green #00FF00, warm brown hands on the keyboard,
   grey knit sleeve, white coffee mug, small plant, soft morning window light
   from the left, 35mm, shallow depth of field.
2. Trackpad close up, 2K: same hand and sleeve, index finger on the trackpad.
Key the green screens and composite original UI through a homography.

SCREEN UI (HTML rendered by headless Chromium, Inter for browser chrome)
Original, generic search engine called "find." (no real search engine name,
logo or layout). Query typed: web design Midrand. Results: a map card with a
teal pin labelled Nimble Tech Solutions, then Nimble Tech Solutions as the first
listing ("Website design and development in Midrand"; snippet lists the five
services and the area). Other listings are generic guides and listings with no
business names. No ratings, reviews, prices or results anywhere. The website
reuses only advert 1's structure: nav strip, teal hero with Your business,
online, two content blocks (DejaVu Sans, brand colours).

TIMELINE (frames)
0 to 34 wide desk; 34 to 80 push to the search box; 48 to 108 typing with
keystroke sounds; 120 Enter; 128 results page, items reveal from 142 as the
camera settles on the results column; 150 pin drops; 172 to 204 cursor to the
Nimble Tech Solutions result; 212 to 235 cut to trackpad, click at 222; 236 cut
back to the browser, website loads from 246; 328 to 398 pull back to the wide
desk, phone wakes at 350 showing the mobile site; 400 crossfade to the teal end
card. End card: shapes settle near the top (404 to 428), then logo (414),
Websites and digital services (424), WhatsApp 068 178 9708 (432), Midrand,
Johannesburg, Remote (440), all static from frame 450 to 479. End card text is
centred on the safe zone (x 96 to 904), not on the frame.

BRAND: teal 115E67, warm white F7F5F0, mist D9ECEC, ink 18282A, apricot
F2B66D. DejaVu Sans and DejaVu Sans Bold for non UI text. Brand name exactly
Nimble Tech Solutions. UK English, no hyphens or dashes in visible copy.

SOUND: original numpy synthesis. 96 bpm soft low pulse, warm pad (Dmaj7, Bm9,
Gmaj7, resolving to Dadd9 on the end card), quiet keystrokes, Enter, map blip,
trackpad click, soft page load swell, phone chime, logo chime. Gentle peak
limiter, then two pass ffmpeg loudnorm, linear, I -14 LUFS, TP -2.7 dBTP; AAC
192k. Measure loudness and true peak on the finished MP4.

CHECKS: full size stills at frames 20, 100, 200, 222, 300, 365, 406, 470;
project every readable text box through the camera per frame and test against
the safe zone (x 96 to 904, y 154 to 1536); strip container metadata and the
x264 SEI; scan files for tool names.

REPRODUCE: see advert7/BUILD.md (python3 src/make_states.py; node
src/render_ui.js; python3 src/composite.py; python3 src/audio.py; loudnorm two
pass; src/encode.sh; python3 src/verify.py).
