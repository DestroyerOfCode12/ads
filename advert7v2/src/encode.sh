#!/usr/bin/env bash
# Encodes frames + normalised mix into the sound and silent deliverables, metadata stripped.
# Encode to elementary streams first, then remux by stream copy, so no encoder tag is written.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=deliverables; T=build/enc
mkdir -p "$OUT" "$T"
ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i build/frames/f%04d.png \
  -c:v libx264 -preset slow -crf 19 -maxrate 20M -bufsize 40M -profile:v high -pix_fmt yuv420p \
  -vf scale=out_color_matrix=bt709 -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -bsf:v filter_units=remove_types=6 -frames:v 480 -flags:v +bitexact "$T/video.mp4"
ffmpeg -hide_banner -loglevel error -y -i build/mix_norm.wav -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -flags:a +bitexact "$T/audio.m4a"
STRIP=(-map_metadata -1 -map_metadata:s -1 -map_chapters -1 -fflags +bitexact -movflags +faststart
       -metadata:s:v handler_name= -metadata:s:a handler_name=)
ffmpeg -hide_banner -loglevel error -y -i "$T/video.mp4" -i "$T/audio.m4a" -map 0:v -map 1:a -c copy \
  -t 16 "${STRIP[@]}" "$OUT/nimble_tech_solutions_advert7_shop_opens_sound.mp4"
ffmpeg -hide_banner -loglevel error -y -i "$T/video.mp4" -map 0:v -c copy -an \
  "${STRIP[@]}" "$OUT/nimble_tech_solutions_advert7_shop_opens_silent.mp4"
python3 - <<'PY'
from PIL import Image
im = Image.open('build/frames/f0290.png').convert('RGB')
im.save('deliverables/nimble_tech_solutions_advert7_shop_opens_poster.png', optimize=True)   # PIL writes no text chunks
im.save('deliverables/nimble_tech_solutions_advert7_shop_opens_poster.jpg', quality=92, optimize=True)  # no EXIF passed
PY
echo done
