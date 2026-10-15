# Phase 2 animation handoff

Required per character: genuine **idle**, **walk**, and **sleep** sequences.
Use the existing character identities; preserve transparent edges and opaque eyes.
Walking must articulate arms/legs through a coherent stride. Sleeping needs an
appropriate sleeping pose and subtle breathing, not a standing/peeking still.

Each sequence belongs in `characters/<character-id>/animations/<state>/` as
zero-padded `frame_00.png`, `frame_01.png`, etc. Use identical 512x512 or 768x768
RGBA canvases, a consistent anchor, stable scale and lighting, transparent
padding, and no clipped hands/feet. Keep the originals or layered source files.

Include an `animation_manifest.json` per character with this structure:

```json
{
  "version": 1,
  "canvas": [512, 512],
  "animations": {
    "walk": {
      "fps": 12,
      "loop": true,
      "direction": "right",
      "mirror_allowed": true,
      "anchor": [256, 488],
      "frames": ["animations/walk/frame_00.png", "animations/walk/frame_01.png"],
      "offsets": [[0, 0], [0, 0]],
      "source": "relative/path/to/authored-source"
    }
  }
}
```

This is a handoff specification, not a claim that the current animation engine
already consumes manifests. Runtime metadata support belongs to Phase 5.

Before acceptance, run the asset audit and review each sequence on light/dark
backgrounds at 150–350px display size. The audit rejects translation-only stills,
missing frames, inconsistent sizes and missing transparency. Visual review must
also confirm natural articulation, costume identity, proportions, and seamless
loop boundaries. A changing image hash alone is not proof of quality.

Free local authoring may use a layered 2D rig or a rigged Blender model, but the
source must actually contain separable body parts and suitable poses. Six flat
reference JPEGs alone are not a finished animation library.
