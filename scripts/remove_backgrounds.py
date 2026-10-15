"""Remove background from all 6 user-provided images using edge-connected flood-fill."""
import os
import sys
import math
import site
from pathlib import Path
from collections import deque

# Ensure site packages available
sys.path.insert(0, site.getusersitepackages())
sys.path.insert(0, os.path.expanduser(r"~\AppData\Roaming\Python\Python313\site-packages"))

from PIL import Image, ImageFilter

def remove_background_floodfill(img_path: Path, tolerance: float = 38.0) -> Image.Image:
    """
    Remove background by flood-filling from all image boundaries.
    Inner white regions (like Spider-Man eye lenses or webs) remain 100% opaque.
    """
    img = Image.open(img_path).convert("RGB")
    w, h = img.size
    pixels = img.load()

    # Sample corners to find background color
    corners = [
        pixels[0, 0],
        pixels[w - 1, 0],
        pixels[0, h - 1],
        pixels[w - 1, h - 1],
        pixels[w // 2, 0],
        pixels[0, h // 2],
        pixels[w - 1, h // 2]
    ]
    # Median background color
    bg_r = sorted([c[0] for c in corners])[len(corners) // 2]
    bg_g = sorted([c[1] for c in corners])[len(corners) // 2]
    bg_b = sorted([c[2] for c in corners])[len(corners) // 2]

    def color_dist(c):
        return math.sqrt((c[0] - bg_r) ** 2 + (c[1] - bg_g) ** 2 + (c[2] - bg_b) ** 2)

    # Queue for BFS flood-fill
    queue = deque()
    visited = bytearray(w * h)

    def idx(x, y):
        return y * w + x

    # Seed all boundary pixels matching background color
    for x in range(w):
        for y in [0, h - 1]:
            if not visited[idx(x, y)] and color_dist(pixels[x, y]) <= tolerance:
                visited[idx(x, y)] = 1
                queue.append((x, y))

    for y in range(h):
        for x in [0, w - 1]:
            if not visited[idx(x, y)] and color_dist(pixels[x, y]) <= tolerance:
                visited[idx(x, y)] = 1
                queue.append((x, y))

    # Perform BFS to expand background
    while queue:
        cx, cy = queue.popleft()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                n_idx = idx(nx, ny)
                if not visited[n_idx]:
                    if color_dist(pixels[nx, ny]) <= tolerance:
                        visited[n_idx] = 1
                        queue.append((nx, ny))

    # Build RGBA image
    rgba = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    rgba_pixels = rgba.load()

    for y in range(h):
        for x in range(w):
            if visited[idx(x, y)]:
                rgba_pixels[x, y] = (0, 0, 0, 0)
            else:
                dist = color_dist(pixels[x, y])
                r, g, b = pixels[x, y]
                # Soften edge if close to tolerance
                if dist < tolerance + 15:
                    alpha = int(min(255, max(0, (dist - tolerance + 5) / 20.0 * 255)))
                    rgba_pixels[x, y] = (r, g, b, alpha)
                else:
                    rgba_pixels[x, y] = (r, g, b, 255)

    # Crop to non-transparent bounding box
    bbox = rgba.getbbox()
    if bbox:
        pad = 6
        crop_box = (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(w, bbox[2] + pad),
            min(h, bbox[3] + pad)
        )
        rgba = rgba.crop(crop_box)

    return rgba

def main():
    img_dir = Path(r"g:\Languages\Projects\Pet\Images")
    out_dir = Path(r"g:\Languages\Projects\Pet\Images_transparent")
    out_dir.mkdir(parents=True, exist_ok=True)

    target_files = [
        "miles  1.jpg",
        "miles 2.jpg",
        "miles 3.jpg",
        "spiderman 1.jpg",
        "spiderman 2.jpg",
        "spiderman 3.jpg"
    ]

    for fname in target_files:
        src = img_dir / fname
        if not src.exists():
            print(f"File not found: {src}")
            continue

        clean_name = fname.replace("  ", " ").replace(".jpg", ".png")
        print(f"Processing {fname} -> {clean_name}...")
        
        # Miles 2 has a grey background, use slightly lower tolerance to preserve ledge & hand
        tol = 32.0 if "miles 2" in fname else 42.0
        transparent_img = remove_background_floodfill(src, tolerance=tol)
        
        dest = out_dir / clean_name
        transparent_img.save(dest, "PNG")
        print(f"Saved {dest} (Size: {transparent_img.size})")

if __name__ == "__main__":
    main()
