#!/usr/bin/env bash
# Encodes three deliverables: with voiceover, music and effects only, and silent. Metadata stripped.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=deliverables; T=build/enc; NAME=nimble_tech_solutions_still_online
mkdir -p "$OUT" "$T"
ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i build/frames/f%04d.png \
  -c:v libx264 -preset slow -crf 19 -maxrate 20M -bufsize 40M -profile:v high -pix_fmt yuv420p \
  -vf scale=out_color_matrix=bt709 -color_primaries bt709 -color_trc bt709 -colorspace bt709 \
  -bsf:v filter_units=remove_types=6 -frames:v 600 -flags:v +bitexact "$T/video.mp4"
STRIP=(-map_metadata -1 -map_metadata:s -1 -map_chapters -1 -fflags +bitexact -movflags +faststart -metadata:s:v handler_name= -metadata:s:a handler_name=)
for v in vo novo; do
  src=build/mix_norm.wav; [ "$v" = novo ] && src=build/mix_norm_novo.wav
  ffmpeg -hide_banner -loglevel error -y -i "$src" -c:a aac -b:a 192k -ar 48000 -ac 2 -flags:a +bitexact "$T/audio_$v.m4a"
done
ffmpeg -hide_banner -loglevel error -y -i "$T/video.mp4" -i "$T/audio_vo.m4a" -map 0:v -map 1:a -c copy -t 20 "${STRIP[@]}" "$OUT/${NAME}_voiceover.mp4"
ffmpeg -hide_banner -loglevel error -y -i "$T/video.mp4" -i "$T/audio_novo.m4a" -map 0:v -map 1:a -c copy -t 20 "${STRIP[@]}" "$OUT/${NAME}_music.mp4"
ffmpeg -hide_banner -loglevel error -y -i "$T/video.mp4" -map 0:v -c copy -an "${STRIP[@]}" "$OUT/${NAME}_silent.mp4"
python3 - <<'PY'
from PIL import Image
im = Image.open('build/frames/f0240.png').convert('RGB')
im.save('deliverables/nimble_tech_solutions_still_online_poster.png', optimize=True)
im.save('deliverables/nimble_tech_solutions_still_online_poster.jpg', quality=92, optimize=True)
PY
echo done
