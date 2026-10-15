# Local artwork rebuild

Run `python scripts/rebuild_character_art.py` to reproduce the current sprites
from the original JPEGs in `Images/`, using open-source Pillow. No API key,
model download, or payment is required. Originals are preserved.

This restores and polishes existing artwork; it is not a newly generated design.
White lenses remain opaque. Only exterior background and the explicitly marked
arm gap are removed. Every frame uses a padded 512 by 512 transparent canvas.
Alpha is composited once to avoid faded edges. Idle and movement use subtle
translation cycles, not independently drawn limb animation. Miles uses three
distinct source poses: full-body for idle/walk/run/land, peeking for climbing,
perching/hanging/sleep, and the web pose for jump/fall/swing/interact/dragged.
The web remains part of that pose, with transparent spaces between its strands.

The older process_character_assets.py and integrate_character_poses.py scripts
are legacy pipelines and should not be used to regenerate these assets.

## Articulated animation build

After the source rebuild, run `python scripts/build_articulated_assets.py` to
render the eight new clips per character. This step replaces the earlier bobbing
idle/walk/run/sleep assets with independent head, torso, arm and leg motion.
The `rig/` PNG layers and `rig.json` retain the editable cutout source. Timing,
loops, anchors, directions, frame paths and offsets live in animation_manifest.json.
The engine now reads per-character FPS/loop metadata. Remaining single-pose
activities continue using the previously selected artwork until later animation work.
