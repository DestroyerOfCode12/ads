"""All timing for advert 7 v2 (frames at 30 fps, 480 total)."""
import json, os
FPS, N = 30, 480
S1, S2, S3, S4, S5 = (0, 84), (84, 150), (150, 240), (240, 330), (330, 396)
SHUTTER = (8, 58)          # shutter rolls up
LIGHTS = 60                # interior lights flicker on (seen through the glass)
BUZZ = 156                 # phone vibrates
WAKE = 160                 # phone screen wakes
NOTE = 166                 # notification slides in
SITE_LOAD = 250            # website loads on the laptop
FLIP = (338, 356)          # door sign turns from Closed to Open
END = 384                  # crossfade into the end card (384 to 396)
END_ITEMS = dict(arc=(386, 412), logo=(398, 410), tag=(408, 418), wa=(416, 426), area=(424, 434))
if __name__ == '__main__':
    os.makedirs('build', exist_ok=True)
    json.dump({k: v for k, v in globals().items() if k.isupper()}, open('build/timing.json', 'w'))
    print('timing written')
