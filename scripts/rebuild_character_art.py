"""Rebuild clean RGBA sprites locally with Pillow; no API or model download.

Only edge-connected white is removed. Enclosed white eye lenses stay opaque.
All poses use one padded canvas, and compositing preserves alpha exactly once.
"""
import json
import math
from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SIZE = 512


def extract(path):
    source = Image.open(path).convert("RGB")
    # Padding connects background regions even when the source touches an edge.
    rgb = Image.new("RGB", (source.width + 4, source.height + 4), "white")
    rgb.paste(source, (2, 2))
    threshold = {"miles 2.jpg": 145, "miles 3.jpg": 180}.get(path.name, 215)
    mask = rgb.point(lambda v: 255 if v >= threshold else 0).convert("RGB")
    # A pixel must be neutral and bright on every channel to be background.
    from PIL import ImageChops, ImageDraw
    r, g, b = mask.split()
    white = ImageChops.darker(ImageChops.darker(r, g), b)
    if path.name == "miles 3.jpg":
        # Keep both enclosed lenses, but clear white cells inside the web prop.
        for point in ((332, 442), (451, 446)):
            ImageDraw.floodfill(white, point, 64, thresh=0)
        white = white.point(lambda v: 128 if v == 255 else v)
    else:
        ImageDraw.floodfill(white, (0, 0), 128, thresh=0)
    # This pose encloses background between its bent arm and torso.
    # Explicit background seed keeps the lens regions protected.
    if path.name == "spiderman 1.jpg":
        ImageDraw.floodfill(white, (449, 408), 128, thresh=0)
    alpha = white.point(lambda v: 0 if v == 128 else 255)
    # Only feather the silhouette; never key white out of the foreground.
    alpha = alpha.filter(ImageFilter.GaussianBlur(0.45))
    out = rgb.convert("RGBA")
    out.putalpha(alpha)
    box = alpha.point(lambda v: 255 if v > 8 else 0).getbbox()
    return out.crop(box)


def canvas(sprite):
    sprite = sprite.copy()
    sprite.thumbnail((448, 464), Image.Resampling.LANCZOS)
    frame = Image.new("RGBA", (SIZE, SIZE))
    frame.alpha_composite(sprite, ((SIZE - sprite.width) // 2, SIZE - 24 - sprite.height))
    return frame


def main():
    sources = {
        "miles_morales": ["miles  1.jpg", "miles 2.jpg", "miles 3.jpg"],
        "tom_holland": ["spiderman 1.jpg", "spiderman 2.jpg", "spiderman 3.jpg"],
    }
    for character, names in sources.items():
        directory = ROOT / "characters" / character
        poses = [canvas(extract(ROOT / "Images" / name)) for name in names]
        pose_names = ("idle", "peeking", "web") if character == "miles_morales" else ("idle", "running", "crouching")
        for name, pose in zip(pose_names, poses):
            pose.save(directory / "sprites" / f"{name}.png")
        poses[0].save(directory / "preview.png")
        profile = json.loads((directory / "character.json").read_text(encoding="utf-8"))
        for state in profile["supported_animations"]:
            index = 1 if state in ("walk", "run", "swing", "fall", "climb_up", "climb_down") else 2 if state in ("perch", "land", "jump", "sleep", "hang", "wall_slide") else 0
            if character == "miles_morales":
                index = 1 if state in ("climb_up", "climb_down", "perch", "hang", "wall_slide", "sleep") else 2 if state in ("jump", "fall", "swing", "interact", "dragged") else 0
            pose = poses[index]
            output = directory / "animations" / state
            output.mkdir(parents=True, exist_ok=True)
            # Remove only generated frame files inside this character's state.
            for old in output.glob("frame_*.png"):
                old.unlink()
            count = 12 if state in ("idle", "walk", "run") else 1
            for i in range(count):
                phase = 2 * math.pi * i / count
                frame = Image.new("RGBA", (SIZE, SIZE))
                bob = round(3 * math.sin(phase)) if state == "idle" else -round(5 * abs(math.sin(phase))) if count > 1 else 0
                frame.alpha_composite(pose, (0, bob))
                frame.save(output / f"frame_{i:02d}.png")
        print(f"Rebuilt {character}: opaque lenses, transparent silhouette, padded 512px frames")


if __name__ == "__main__":
    main()
