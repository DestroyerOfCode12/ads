"""Two pass, linear EBU R128 normalisation: build/mix_raw.wav -> build/mix_norm.wav (I -14 LUFS, TP -2.7 dBTP)."""
import json, os, subprocess
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build')
base = 'loudnorm=I=-14:TP=-2.7:LRA=11'
r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', os.path.join(B, 'mix_raw.wav'), '-af', base + ':print_format=json', '-f', 'null', '-'], capture_output=True, text=True)
m = json.loads(r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1])
af = base + (':measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:measured_thresh={input_thresh}'
             ':offset={target_offset}:linear=true:print_format=json').format(**m)
r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-y', '-i', os.path.join(B, 'mix_raw.wav'), '-af', af, '-ar', '48000', '-c:a', 'pcm_s24le', os.path.join(B, 'mix_norm.wav')], capture_output=True, text=True)
o = json.loads(r.stderr[r.stderr.rindex('{'):r.stderr.rindex('}') + 1])
print('pass 1 input %s LUFS %s dBTP; pass 2 output %s LUFS %s dBTP, type %s' % (m['input_i'], m['input_tp'], o['output_i'], o['output_tp'], o['normalization_type']))
