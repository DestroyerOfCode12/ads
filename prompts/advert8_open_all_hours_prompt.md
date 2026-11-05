Prompt for Claude Code: Nimble Tech Solutions advert 8, Open all hours

Build a 16 second vertical video advert for my business, Nimble Tech
Solutions. This is advert 8 in an ongoing campaign. Adverts 1 to 6 are
flat vector illustration; advert 7 (Shop opens) moved to a 3D scene
rendered in Blender. Advert 8 continues in Blender and reuses advert 7's
shop set (advert7v2/src/scene.py and its Poly Haven assets) so the
campaign has one consistent world: the same corner shop on the same
Johannesburg street. This advert is about web hosting and business email
that keep working when the owner is not there.

NO PEOPLE
No people anywhere: no hands, faces, figures, silhouettes or reflections
of people. The story is told through the place, light and objects.

OUTPUT
1080 by 1920 pixels, 30 fps, 480 frames (16.000 seconds exactly), MP4.
Deliver a version with sound and a separate version with no audio stream
at all.

BUSINESS
Nimble Tech Solutions is an owner run web and IT business based in Midrand,
Gauteng, serving small business owners in greater Johannesburg and remote
clients. Services: website design and development, business email setup
and management, web hosting, search engine optimisation (SEO), video
advertising. Contact: 068 178 9708. Use exactly Nimble Tech Solutions as
the visible brand name. Do not shorten it, do not add a legal suffix, and
do not imply completed BBBEE certification (it is still pending).

LOGO, PALETTE AND FONT
Digital teal 115E67, warm white F7F5F0, mist D9ECEC, deep ink 18282A,
apricot F2B66D, and the approved stacked Nimble Tech Solutions logo lockup
(use assets/logo_white.png if I have supplied it; if not, use the same
typographic stand in as advert 7 and say so clearly). DejaVu Sans and
DejaVu Sans Bold for any on screen text that is not part of a UI mockup or
a prop in the scene.

CREATIVE CONCEPT
Open all hours. The shop closes for the night, but its website and email
keep working. One continuous day to night to morning time lapse of the
same street and shop, then a close look at the screens that never sleep,
then the shop opening again at sunrise, ending on the end card from
advert 7. The point: hosting and email that are always on, set up and
looked after by Nimble Tech Solutions.

STORYBOARD (timings are a guide; time them to the music)
Frames 0 to about 120: exterior, late afternoon. The camera slowly cranes
down the street towards the shop. The sun sets in a time lapse (animate
the sun angle, colour and strength and blend to a night HDRI), shadows
sweep across the facade, the street lamp flickers on, the shutter rolls
down (advert 7's shutter animation reversed), the shop goes dark.
Frames about 120 to 270: interior at night, lit only by moonlight through
the glass and the two screens. The laptop on the counter stays awake
showing the website from advert 1's structure (nav strip, hero block with
Your business, online, two content blocks). The phone beside it lights up
briefly with a generic email notification (an invented sender such as
Website enquiry, no real names, no addresses, no numbers of messages). A
slow dolly along the counter; the clock on the wall (Poly Haven wall_clock)
moves through the night in a time lapse.
Frames about 270 to 400: dawn. Light floods in, the shutter rolls up from
inside (seen from behind the counter), the door sign turns to Open, the
camera pushes into the teal sign as in advert 7.
Frames about 400 to 479: advert 7's redesigned end card (sunrise over a
horizon line, logo, then Websites and digital services, WhatsApp 068 178
9708, Midrand, Johannesburg, Remote), fully static and readable for at
least the last 1.5 seconds.

BLENDER APPROACH (based on what advert 7 taught us)
1. Build in Blender with Python (bpy 5.x from pip, Cycles on the CPU; Eevee
   needs a GPU and is not available here). Reuse and extend advert 7's
   scene.py rather than starting again: one .blend, one shop set, several
   cameras switched with timeline markers.
2. Use only CC0 assets (Poly Haven models, textures and HDRIs: a sunset or
   golden hour HDRI, a night HDRI, a dawn HDRI), downloaded by a fetch
   script and not committed to git. List every asset used in BUILD.md.
3. Screens are image sequences rendered from HTML with headless Chromium
   and mapped onto emissive screen planes, so UI text is real typography.
4. Animate light and time properly: sun rotation and colour, world HDRI
   blends, lamp emission with a flicker, window light on the floor
   sweeping across. Real camera moves through the 3D set (parallax), not
   pans over still images.
5. Render budget: on this 4 core machine advert 7 rendered at about 30
   seconds per frame at 648x1152 with 12 samples and OpenImageDenoise.
   Before the full render, estimate the total time from 3 test frames and
   tell me the estimate. Keep geometry light in shots that do not need it
   (hide the jacaranda tree indoors), cap bounces, and render at 0.6
   resolution, then upscale with the finishing pass (grade, gentle bloom,
   lateral chromatic aberration, vignette, film grain). Frame text shots
   tightly so text stays crisp after the upscale.
6. Render full size test stills of the busiest frame in every shot and look
   at them before the full render. Fix z fighting, missing textures
   (magenta), signs or screens facing the wrong way, and shots that are
   too dark.
7. Run the render in the background and send me a short preview of the
   first finished shot so I can react before everything is rendered.

COPY AND CLAIMS
UK English. No hyphens, en dashes or em dashes anywhere in visible copy.
No prices, client names, testimonials, star ratings, review counts,
uptime percentages or results anywhere, including inside UI mockups and on
props. Do not claim 24 hour support, guaranteed uptime or any specific
response time. No slogan or extra claim beyond Your business, online, the
door sign words Open and Closed, and the end card lines.

SOUND
No narration and no third party voice service. Generate an original score
and sound effects in code, no samples: an evening to morning arc (the
music thins out and goes quiet and dreamy at night, then lifts at dawn),
foley for the shutter, the street lamp, a distant night ambience (crickets,
far traffic, all synthesised), a soft notification tone, the sign flip.
Effects stay under the music. Two pass linear loudness normalisation to
about minus 14 LUFS integrated, pre encode true peak around minus 2.5 dBTP
or lower, and check loudness and true peak on the finished MP4's own audio
track.

LAYOUT
Keep all genuinely important text (UI headline, notification text, sign
word, logo and end card lines) inside y 154 to 1536, with a 96 pixel left
margin and 176 pixel right margin. Verify this by projecting each text
region through the Blender camera for every frame where it is readable,
as advert 7's check_safe.py does.

CHECKS AND DELIVERABLES
Verify and report resolution, frame rate, duration, frame count, audio
presence, loudness and true peak measured on the finished MP4, sound to
picture sync (cross correlate the decoded MP4 audio with the pre encode
mix), the copy and claims scan, and the safe margin check. Strip
container metadata and the encoder SEI, and scan the files for tool names.
Deliver a sound MP4, a silent MP4, a poster frame, a short reusable prompt,
BUILD.md with the exact rebuild steps and asset list, commit and push to a
branch (not main), and show me the video here when it is done.
