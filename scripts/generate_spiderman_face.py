"""Generate an iconic 'Red Spider-Man Face Only' logo with transparent background."""
from pathlib import Path
from PIL import Image, ImageDraw

def generate_spiderman_face():
    output_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "spiderman_face.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Spider-Man mask contour (teardrop-oval face shape)
    # Head contour points
    mask_points = [
        (256, 32),   # Top center of head
        (350, 48),
        (420, 100),
        (460, 180),
        (465, 270),
        (440, 360),
        (380, 435),
        (320, 478),
        (256, 496),  # Chin
        (192, 478),
        (132, 435),
        (72, 360),
        (47, 270),
        (52, 180),
        (92, 100),
        (162, 48),
    ]

    # Draw vibrant crimson red mask
    draw.polygon(mask_points, fill=(229, 9, 20, 255), outline=(20, 20, 26, 255), width=8)

    # Web lines radiating from bridge of the nose (center between eyes)
    center = (256, 280)
    radial_targets = [
        (256, 36),
        (350, 52),
        (420, 105),
        (460, 185),
        (463, 275),
        (438, 365),
        (378, 438),
        (318, 480),
        (256, 492),
        (194, 480),
        (134, 438),
        (74, 365),
        (49, 275),
        (54, 185),
        (94, 105),
        (164, 52),
    ]

    for target in radial_targets:
        draw.line([center, target], fill=(20, 20, 26, 170), width=4)

    # Concentric curved web lines
    for scale in [0.35, 0.60, 0.82]:
        loop = []
        for target in radial_targets:
            px = center[0] + (target[0] - center[0]) * scale
            py = center[1] + (target[1] - center[1]) * scale
            loop.append((px, py))
        for i in range(len(loop)):
            p1 = loop[i]
            p2 = loop[(i + 1) % len(loop)]
            draw.line([p1, p2], fill=(20, 20, 26, 150), width=3)

    # Large iconic white Spider lenses with thick black rim
    # Left eye outline (black)
    left_eye_outer = [
        (240, 235),
        (120, 205),
        (92, 280),
        (160, 350),
        (242, 305),
    ]
    draw.polygon(left_eye_outer, fill=(20, 20, 26, 255), outline=(15, 15, 20, 255), width=4)

    # Left eye inner (white)
    left_eye_inner = [
        (232, 245),
        (132, 222),
        (108, 280),
        (165, 335),
        (232, 298),
    ]
    draw.polygon(left_eye_inner, fill=(255, 255, 255, 255))

    # Right eye outline (black)
    right_eye_outer = [
        (272, 235),
        (392, 205),
        (420, 280),
        (352, 350),
        (270, 305),
    ]
    draw.polygon(right_eye_outer, fill=(20, 20, 26, 255), outline=(15, 15, 20, 255), width=4)

    # Right eye inner (white)
    right_eye_inner = [
        (280, 245),
        (380, 222),
        (404, 280),
        (347, 335),
        (280, 298),
    ]
    draw.polygon(right_eye_inner, fill=(255, 255, 255, 255))

    img.save(output_path, "PNG")
    print(f"Generated Spider-Man face logo: {output_path}")

    # Also update tray icon and spider.ico with the face logo
    tray_path = output_path.parent / "tray.png"
    img.save(tray_path, "PNG")

    ico_path = output_path.parent / "spider.ico"
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=sizes)
    print(f"Updated tray.png and spider.ico with face logo")

if __name__ == "__main__":
    generate_spiderman_face()
