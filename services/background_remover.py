"""
Automatic intelligent background removal for custom character artwork.

Supports:
1. Native transparency pass-through (respects existing clean transparent PNGs).
2. AI-driven segmentation via rembg (u2netp / u2net), removing complex backgrounds,
   solid colors, gradients, floor contact shadows, and watermark text.
3. Fast, zero-dependency algorithmic fallback using adaptive multi-seed flood-fill
   with edge feathering if AI modules are unavailable or fail.
4. Alpha speck / isolated noise filtering to ensure only the character is isolated.
"""

from collections import deque
import logging
import math
import os
from pathlib import Path
import site
import sys
from typing import Callable, Optional

from PIL import Image, ImageFilter, ImageOps

logger = logging.getLogger("SpiderBuddy.BackgroundRemover")


def ensure_site_packages() -> None:
    """Ensure user roaming and local site-packages are added to sys.path."""
    try:
        user_site = site.getusersitepackages()
        if os.path.exists(user_site) and user_site not in sys.path:
            sys.path.insert(0, user_site)
    except Exception:
        pass

    try:
        version = f"Python{sys.version_info.major}{sys.version_info.minor}"
        roaming_site = str(Path.home() / "AppData" / "Roaming" / "Python" / version / "site-packages")
        if os.path.exists(roaming_site) and roaming_site not in sys.path:
            sys.path.insert(0, roaming_site)
    except Exception:
        pass


def detect_and_clean_checkerboard(img: Image.Image) -> Optional[Image.Image]:
    """Detect and strip fake checkerboard grids embedded in alpha or RGB."""
    if "A" not in img.getbands():
        return None
    try:
        ensure_site_packages()
        import numpy as np
        from scipy import ndimage

        alpha = np.array(img.getchannel("A"))
        solid = alpha > 100
        labeled, num_features = ndimage.label(solid)
        if num_features < 40:
            return None

        sizes = ndimage.sum(solid, labeled, range(1, num_features + 1))
        tiny_squares = sum(1 for s in sizes if s <= 64)
        if tiny_squares < 50:
            return None

        logger.info("Detected fake checkerboard pattern with %d grid squares; cleaning...", tiny_squares)
        max_size = max(sizes)
        min_size = max(350, max_size * 0.008)
        keep = np.isin(labeled, [i + 1 for i, s in enumerate(sizes) if s >= min_size])
        keep = ndimage.binary_fill_holes(keep)

        # Check for achromatic border tiles (checkerboard gray/white squares)
        rgb = np.array(img.convert("RGB"))
        r = rgb[:, :, 0].astype(int)
        g = rgb[:, :, 1].astype(int)
        b = rgb[:, :, 2].astype(int)
        chroma = np.maximum(np.maximum(np.abs(r - g), np.abs(r - b)), np.abs(g - b))
        neutral_bright = (chroma <= 12) & (r >= 120)

        eroded = ndimage.binary_erosion(keep, iterations=6)
        boundary_zone = keep & ~eroded
        checker_boundary = boundary_zone & neutral_bright

        cleaned = keep & ~checker_boundary
        cleaned = ndimage.binary_fill_holes(cleaned)
        cleaned = ndimage.binary_opening(cleaned, structure=np.ones((2, 2)))
        cleaned = ndimage.binary_closing(cleaned, structure=np.ones((3, 3)))

        mask = Image.fromarray(np.where(cleaned, 255, 0).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.65))
        out = img.copy()
        out.putalpha(mask)
        return out
    except Exception as exc:
        logger.debug("Checkerboard detection skipped: %s", exc)
        return None


def is_already_transparent(image: Image.Image) -> bool:
    """Check if the image is already an isolated character cutout with a transparent background."""
    if "A" not in image.getbands():
        return False
    alpha = image.getchannel("A")
    extrema = alpha.getextrema()
    # If the minimum alpha is opaque or nearly opaque, background is not transparent
    if extrema[0] >= 128:
        return False

    w, h = image.size
    alpha_pixels = alpha.load()
    border_pixels = []
    step_x = max(1, w // 40)
    step_y = max(1, h // 40)

    # Sample top and bottom rows
    for x in range(0, w, step_x):
        border_pixels.append(alpha_pixels[x, 0])
        border_pixels.append(alpha_pixels[x, h - 1])
    # Sample left and right columns
    for y in range(0, h, step_y):
        border_pixels.append(alpha_pixels[0, y])
        border_pixels.append(alpha_pixels[w - 1, y])

    if not border_pixels:
        return False

    # If 65% or more of the perimeter is transparent (alpha <= 15), check inner bbox
    transparent_count = sum(1 for a in border_pixels if a <= 15)
    ratio = transparent_count / len(border_pixels)
    if ratio < 0.65:
        return False

    # Check inner bounding box: if there is an inner rectangular box of background,
    # the 4 corners of the inner bounding box will have high alpha.
    bbox = alpha.getbbox()
    if bbox:
        bx0, by0, bx1, by1 = bbox
        if (bx1 - bx0) >= w * 0.5 and (by1 - by0) >= h * 0.5:
            # Check corners of inner bounding box
            inner_corners = [
                alpha_pixels[bx0, by0],
                alpha_pixels[bx1 - 1, by0],
                alpha_pixels[bx0, by1 - 1],
                alpha_pixels[bx1 - 1, by1 - 1]
            ]
            # In a real character silhouette, corners of bbox are almost always empty/transparent
            if sum(1 for a in inner_corners if a > 60) >= 3:
                return False

    return True


def filter_alpha_specks(img: Image.Image, min_component_ratio: float = 0.015) -> Image.Image:
    """Remove detached tiny alpha noise, watermark specks, and floor shadow remnants."""
    try:
        ensure_site_packages()
        import numpy as np
        from scipy import ndimage

        alpha = np.array(img.getchannel("A"))
        binary = alpha > 20
        labeled, num_features = ndimage.label(binary)
        if num_features > 1:
            sizes = ndimage.sum(binary, labeled, range(1, num_features + 1))
            max_size = max(sizes)
            min_size = max_size * min_component_ratio
            keep_mask = np.isin(labeled, [i + 1 for i, s in enumerate(sizes) if s >= min_size])
            alpha[~keep_mask] = 0
            cleaned = img.copy()
            cleaned.putalpha(Image.fromarray(alpha))
            return cleaned
    except Exception as e:
        logger.debug("Component filtering skipped: %s", e)
    return img


def remove_background_ai(image: Image.Image) -> Image.Image:
    """Remove background using rembg neural network segmentation."""
    ensure_site_packages()
    import rembg

    # Try u2netp first (fast, lightweight, 4.7MB model)
    try:
        session = rembg.new_session("u2netp")
        res = rembg.remove(image, session=session)
    except Exception as exc:
        logger.debug("u2netp session failed, falling back to default rembg session: %s", exc)
        res = rembg.remove(image)

    if res and res.getchannel("A").getbbox():
        return filter_alpha_specks(res)
    raise RuntimeError("AI background removal yielded empty alpha channel.")


def remove_background_algorithmic(img: Image.Image, tolerance: float = 40.0) -> Image.Image:
    """
    Algorithmic fallback: BFS flood-fill from all image outer boundaries.
    Inner regions (like Spider-Man white eye lenses or chest emblems) remain protected.
    """
    rgb = img.convert("RGB")
    w, h = rgb.size
    pixels = rgb.load()

    # Sample perimeter corners and edge midpoints
    sample_points = [
        (0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
        (w // 2, 0), (0, h // 2), (w - 1, h // 2), (w // 2, h - 1),
        (2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)
    ]
    sampled_colors = [pixels[px, py] for px, py in sample_points if 0 <= px < w and 0 <= py < h]
    med_r = sorted(c[0] for c in sampled_colors)[len(sampled_colors) // 2]
    med_g = sorted(c[1] for c in sampled_colors)[len(sampled_colors) // 2]
    med_b = sorted(c[2] for c in sampled_colors)[len(sampled_colors) // 2]
    bg_color = (med_r, med_g, med_b)

    def color_dist(c1, c2):
        return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2)

    visited = bytearray(w * h)
    queue = deque()

    def idx(x, y):
        return y * w + x

    # Seed all boundary pixels matching background color within tolerance
    for x in range(w):
        for y in [0, 1, h - 2, h - 1]:
            if 0 <= y < h:
                i = idx(x, y)
                if not visited[i] and color_dist(pixels[x, y], bg_color) <= tolerance * 1.4:
                    visited[i] = 1
                    queue.append((x, y))

    for y in range(h):
        for x in [0, 1, w - 2, w - 1]:
            if 0 <= x < w:
                i = idx(x, y)
                if not visited[i] and color_dist(pixels[x, y], bg_color) <= tolerance * 1.4:
                    visited[i] = 1
                    queue.append((x, y))

    # BFS flood-fill background
    while queue:
        cx, cy = queue.popleft()
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                n_idx = idx(nx, ny)
                if not visited[n_idx]:
                    if color_dist(pixels[nx, ny], bg_color) <= tolerance:
                        visited[n_idx] = 1
                        queue.append((nx, ny))

    # Create alpha mask with soft anti-aliased edge
    mask = Image.new("L", (w, h), 255)
    mask_pixels = mask.load()
    for y in range(h):
        for x in range(w):
            if visited[idx(x, y)]:
                mask_pixels[x, y] = 0

    mask = mask.filter(ImageFilter.GaussianBlur(0.65))
    rgba = img.convert("RGBA")
    rgba.putalpha(mask)
    return filter_alpha_specks(rgba)


def auto_remove_background(
    image: Image.Image,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Image.Image:
    """
    Main entry point: cleans or removes background from character artwork.
    Preserves transparent PNGs; runs AI segmentation with robust algorithmic fallback.
    """
    # Check for fake checkerboard grids embedded in alpha or image
    checker_cleaned = detect_and_clean_checkerboard(image)
    if checker_cleaned is not None:
        logger.info("Detected and removed fake checkerboard background.")
        return checker_cleaned

    if is_already_transparent(image):
        logger.info("Artwork already has transparent background; preserving alpha.")
        return image.convert("RGBA")

    if progress_callback:
        progress_callback(8, "Removing background and isolating character...")

    # Attempt AI removal
    try:
        logger.info("Attempting AI background removal via rembg...")
        cleaned = remove_background_ai(image)
        if cleaned.getchannel("A").getbbox():
            logger.info("AI background removal succeeded.")
            return cleaned
    except Exception as exc:
        logger.warning("AI background removal unavailable or failed (%s); falling back to algorithmic remover.", exc)

    # Fallback to algorithmic floodfill
    if progress_callback:
        progress_callback(12, "Applying edge-connected background cleanup...")

    cleaned = remove_background_algorithmic(image)
    if not cleaned.getchannel("A").getbbox():
        raise ValueError("Artwork is empty after background removal. Please provide a clear character image.")

    return cleaned
