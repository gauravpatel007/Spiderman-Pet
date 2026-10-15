"""Protect opaque lenses and consistent transparent animation canvases."""
from pathlib import Path

from PIL import Image, ImageDraw

from scripts.rebuild_character_art import extract


def test_white_eye_survives_background_removal(tmp_path):
    image = Image.new("RGB", (100, 100), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 10, 90, 90), fill="black")
    draw.ellipse((30, 30, 55, 55), fill="white")
    path = tmp_path / "hero.png"
    image.save(path)
    result = extract(path)
    white_pixels = [p for p in result.getdata() if min(p[:3]) > 250 and p[3] == 255]
    assert len(white_pixels) > 200
    assert result.getpixel((0, 0))[3] == 0


def test_all_animation_frames_have_padding_and_alpha():
    root = Path(__file__).resolve().parents[1] / "characters"
    for path in root.glob("*/animations/*/*.png"):
        with Image.open(path) as frame:
            assert frame.mode == "RGBA", path
            assert frame.size == (512, 512), path
            alpha = frame.getchannel("A")
            assert alpha.getextrema() == (0, 255), path
            left, top, right, bottom = alpha.getbbox()
            assert left > 0 and top > 0 and right < 512 and bottom < 512, path


def test_miles_has_three_distinct_poses_wired_to_activities():
    root = Path(__file__).resolve().parents[1] / "characters" / "miles_morales"
    poses = [Image.open(root / "sprites" / f"{name}.png").tobytes()
             for name in ("idle", "peeking", "web")]
    assert len(set(poses)) == 3
    for state, index in (("land", 0), ("climb_up", 1), ("swing", 2)):
        with Image.open(root / "animations" / state / "frame_00.png") as frame:
            assert frame.tobytes() == poses[index]
