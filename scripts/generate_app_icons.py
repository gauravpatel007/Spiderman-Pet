"""Generate high-resolution application and tray icons for Spider-Buddy."""
import os
from pathlib import Path
from PIL import Image, ImageDraw

def generate_icons():
    icons_dir = Path(__file__).resolve().parent.parent / "assets" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)

    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Crimson-red circular badge
    margin = 24
    draw.ellipse([margin, margin, size - margin, size - margin], fill=(229, 9, 20, 255), outline=(18, 18, 28, 255), width=16)

    # Inner web concentric circles
    center = (size // 2, size // 2)
    for r in [80, 140, 200]:
        draw.ellipse([center[0] - r, center[1] - r, center[0] + r, center[1] + r], outline=(255, 255, 255, 60), width=6)

    # Spider lenses (eyes)
    # Left eye
    left_eye = [
        (size // 2 - 20, size // 2 - 60),
        (size // 2 - 130, size // 2 - 40),
        (size // 2 - 120, size // 2 + 50),
        (size // 2 - 20, size // 2 + 10),
    ]
    draw.polygon(left_eye, fill=(255, 255, 255, 255), outline=(18, 18, 28, 255))

    # Right eye
    right_eye = [
        (size // 2 + 20, size // 2 - 60),
        (size // 2 + 130, size // 2 - 40),
        (size // 2 + 120, size // 2 + 50),
        (size // 2 + 20, size // 2 + 10),
    ]
    draw.polygon(right_eye, fill=(255, 255, 255, 255), outline=(18, 18, 28, 255))

    # Save high-res PNG
    png_path = icons_dir / "tray.png"
    img.save(png_path, "PNG")
    print(f"Generated {png_path}")

    app_png = icons_dir / "app_icon.png"
    img.save(app_png, "PNG")
    print(f"Generated {app_png}")

    # Save multi-size Windows ICO
    ico_path = icons_dir / "spider.ico"
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=sizes)
    print(f"Generated {ico_path}")

if __name__ == "__main__":
    generate_icons()
