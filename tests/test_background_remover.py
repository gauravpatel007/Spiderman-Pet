"""
Unit and regression tests for automatic background removal.
"""
from pathlib import Path
from PIL import Image, ImageDraw
import pytest

from services.background_remover import (
    auto_remove_background,
    is_already_transparent,
    filter_alpha_specks,
    remove_background_algorithmic,
)
from services.character_import import load_artwork


def test_is_already_transparent_detection():
    # Fully opaque image
    opaque = Image.new("RGBA", (100, 100), (255, 200, 0, 255))
    assert is_already_transparent(opaque) is False

    # Character cutout silhouette (transparent borders & corners)
    transparent = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(transparent)
    draw.ellipse((20, 20, 80, 80), fill=(255, 0, 0, 255))
    assert is_already_transparent(transparent) is True

    # Framed rectangular image inside transparent borders should not be treated as a cutout
    framed = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw_framed = ImageDraw.Draw(framed)
    draw_framed.rectangle((20, 20, 80, 80), fill=(255, 0, 0, 255))
    assert is_already_transparent(framed) is False


def test_remove_background_solid_yellow(tmp_path):
    img = Image.new("RGB", (120, 160), (250, 205, 5))
    draw = ImageDraw.Draw(img)
    # Draw character body
    draw.ellipse((30, 20, 90, 80), fill=(200, 20, 20))
    draw.rectangle((40, 80, 80, 140), fill=(20, 20, 20))
    path = tmp_path / "yellow_char.png"
    img.save(path)

    loaded = load_artwork(path)
    # Check that outer canvas corners are transparent
    assert loaded.getpixel((0, 0))[3] == 0
    assert loaded.getpixel((511, 0))[3] == 0
    # Check that character pixels remain visible
    bbox = loaded.getchannel("A").getbbox()
    assert bbox is not None


def test_remove_background_preserves_inner_white_lenses(tmp_path):
    # White background with dark mask and white eye lenses
    img = Image.new("RGB", (120, 120), "white")
    draw = ImageDraw.Draw(img)
    draw.ellipse((20, 20, 100, 100), fill=(180, 0, 0))
    draw.ellipse((35, 45, 55, 65), fill="black")
    draw.ellipse((40, 50, 50, 60), fill="white")  # inner lens
    path = tmp_path / "spidey_head.png"
    img.save(path)

    cleaned = auto_remove_background(img)
    assert cleaned.getpixel((0, 0))[3] == 0
    # Center lens pixel should remain opaque white
    lens_pixel = cleaned.getpixel((45, 55))
    assert lens_pixel[0] > 230 and lens_pixel[1] > 230 and lens_pixel[2] > 230
    assert lens_pixel[3] > 200


def test_filter_alpha_specks():
    img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Large main body (900 px^2)
    draw.rectangle((20, 20, 50, 50), fill=(255, 0, 0, 255))
    # Tiny stray speck (2 px^2)
    draw.point((90, 90), fill=(255, 255, 255, 255))
    draw.point((91, 91), fill=(255, 255, 255, 255))

    filtered = filter_alpha_specks(img)
    # Speck should be eliminated
    assert filtered.getpixel((90, 90))[3] == 0
    # Main body remains intact
    assert filtered.getpixel((30, 30))[3] == 255
