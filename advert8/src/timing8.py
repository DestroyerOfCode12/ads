"""All timing for advert 8, Open all hours (frames at 30 fps, 480 total)."""
import json, os
FPS, N = 30, 480
S1, S2A, S2B, S3, S4 = (0, 120), (120, 195), (195, 270), (270, 350), (350, 404)
N3D = 404                    # frames rendered in Blender (0..403)
SUNSET = (0, 104)            # sun goes down, world fades to night
LAMP_ON = 64                 # street lamp flickers on
LIGHTS_OFF = 74              # shop lights switch off
SHUTTER_DOWN = (80, 112)
CLOCK = (120, 270, 23.0, 29.5)   # clock runs 23:00 to 05:30 across the night shots
BUZZ = 205; WAKE = 208; NOTE = 212
SUNRISE = (270, 306)
SHUTTER_UP = (276, 322)
LIGHTS_ON = 326
FLIP = (354, 370)
END = 392                    # crossfade into the end card (392 to 404)
END_ITEMS = dict(arc=(394, 420), logo=(406, 418), tag=(416, 426), wa=(424, 434), area=(432, 442))
# names used by the shared finishing code
S5 = S4; SITE_LOAD = S2A[0]
if __name__ == '__main__':
    os.makedirs('build', exist_ok=True)
    json.dump({k: v for k, v in globals().items() if k.isupper()}, open('build/timing.json', 'w'))
    print('timing written')
S2 = S3   # dust in the dawn light
