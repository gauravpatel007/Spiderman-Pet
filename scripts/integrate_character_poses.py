"""Integrate all 6 transparent user images into character animations and poses."""
import math
import os
import shutil
import site
import sys
from pathlib import Path

# Ensure site packages available
sys.path.insert(0, site.getusersitepackages())
sys.path.insert(0, os.path.expanduser(r"~\AppData\Roaming\Python\Python313\site-packages"))

from PIL import Image

def generate_breathing_cycle(base_img: Image.Image, output_dir: Path, num_frames: int = 4):
    """Generate subtle natural breathing/idle frames."""
    output_dir.mkdir(parents=True, exist_ok=True)
    w, h = base_img.size

    for i in range(num_frames):
        frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        angle_rad = 2 * math.pi * i / num_frames
        offset_y = int(round(3 * math.sin(angle_rad)))

        scale_y = 1.0 + 0.018 * math.sin(angle_rad)
        scale_x = 1.0 - 0.009 * math.sin(angle_rad)

        new_w = int(round(w * scale_x))
        new_h = int(round(h * scale_y))

        scaled = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        paste_x = (w - new_w) // 2
        paste_y = (h - new_h) + offset_y

        frame.paste(scaled, (paste_x, paste_y), scaled)
        frame.save(output_dir / f"frame_{i}.png", "PNG")

def generate_walking_cycle(base_img: Image.Image, output_dir: Path, num_frames: int = 6):
    """Generate subtle stepping and bobbing animation frames."""
    output_dir.mkdir(parents=True, exist_ok=True)
    w, h = base_img.size

    for i in range(num_frames):
        frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        phase = 2 * math.pi * i / num_frames

        bob_y = int(round(6 * abs(math.sin(phase))))
        angle = 3.5 * math.sin(phase)

        rotated = base_img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
        paste_x = int(round(3 * math.cos(phase)))
        paste_y = -bob_y

        frame.paste(rotated, (paste_x, paste_y), rotated)
        frame.save(output_dir / f"frame_{i}.png", "PNG")

def save_single_frame_anim(base_img: Image.Image, output_dir: Path):
    """Save static pose as single-frame animation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    base_img.save(output_dir / "frame_0.png", "PNG")

def main():
    root = Path(__file__).resolve().parent.parent
    trans_dir = root / "Images_transparent"
    img_dir = root / "Images"

    miles1 = Image.open(trans_dir / "miles 1.png").convert("RGBA")
    miles2 = Image.open(trans_dir / "miles 2.png").convert("RGBA")
    miles3 = Image.open(trans_dir / "miles 3.png").convert("RGBA")

    spidey1 = Image.open(trans_dir / "spiderman 1.png").convert("RGBA")
    spidey2 = Image.open(trans_dir / "spiderman 2.png").convert("RGBA")
    spidey3 = Image.open(trans_dir / "spiderman 3.png").convert("RGBA")

    # Also save transparent copies directly in Images folder for easy access
    miles1.save(img_dir / "miles 1 (transparent).png", "PNG")
    miles2.save(img_dir / "miles 2 (transparent).png", "PNG")
    miles3.save(img_dir / "miles 3 (transparent).png", "PNG")
    spidey1.save(img_dir / "spiderman 1 (transparent).png", "PNG")
    spidey2.save(img_dir / "spiderman 2 (transparent).png", "PNG")
    spidey3.save(img_dir / "spiderman 3 (transparent).png", "PNG")
    print("Saved transparent PNGs into Images/ folder.")

    # 1. SETUP MILES MORALES
    miles_dir = root / "characters" / "miles_morales"
    (miles_dir / "sprites").mkdir(parents=True, exist_ok=True)
    (miles_dir / "animations").mkdir(parents=True, exist_ok=True)

    miles1.save(miles_dir / "preview.png", "PNG")
    miles1.save(miles_dir / "sprites" / "idle.png", "PNG")
    miles2.save(miles_dir / "sprites" / "peeking.png", "PNG")
    miles3.save(miles_dir / "sprites" / "web.png", "PNG")

    # Miles animation cycles
    generate_breathing_cycle(miles1, miles_dir / "animations" / "idle")
    generate_walking_cycle(miles1, miles_dir / "animations" / "walk")
    generate_walking_cycle(miles1, miles_dir / "animations" / "run")

    save_single_frame_anim(miles3, miles_dir / "animations" / "jump")
    save_single_frame_anim(miles3, miles_dir / "animations" / "fall")
    save_single_frame_anim(miles1, miles_dir / "animations" / "land")

    save_single_frame_anim(miles2, miles_dir / "animations" / "climb_up")
    save_single_frame_anim(miles2, miles_dir / "animations" / "climb_down")
    save_single_frame_anim(miles2, miles_dir / "animations" / "wall_slide")
    save_single_frame_anim(miles2, miles_dir / "animations" / "perch")
    save_single_frame_anim(miles2, miles_dir / "animations" / "hang")
    save_single_frame_anim(miles2, miles_dir / "animations" / "sleep")

    save_single_frame_anim(miles3, miles_dir / "animations" / "swing")
    save_single_frame_anim(miles3, miles_dir / "animations" / "interact")
    save_single_frame_anim(miles3, miles_dir / "animations" / "dragged")

    print("Miles Morales poses and animation states integrated.")

    # 2. SETUP TOM HOLLAND SPIDER-MAN
    tom_dir = root / "characters" / "tom_holland"
    (tom_dir / "sprites").mkdir(parents=True, exist_ok=True)
    (tom_dir / "animations").mkdir(parents=True, exist_ok=True)

    spidey1.save(tom_dir / "preview.png", "PNG")
    spidey1.save(tom_dir / "sprites" / "idle.png", "PNG")
    spidey2.save(tom_dir / "sprites" / "running.png", "PNG")
    spidey3.save(tom_dir / "sprites" / "crouching.png", "PNG")

    # Tom Holland animation cycles
    generate_breathing_cycle(spidey1, tom_dir / "animations" / "idle")
    generate_walking_cycle(spidey2, tom_dir / "animations" / "walk")
    generate_walking_cycle(spidey2, tom_dir / "animations" / "run")

    save_single_frame_anim(spidey3, tom_dir / "animations" / "jump")
    save_single_frame_anim(spidey2, tom_dir / "animations" / "fall")
    save_single_frame_anim(spidey3, tom_dir / "animations" / "land")

    save_single_frame_anim(spidey2, tom_dir / "animations" / "climb_up")
    save_single_frame_anim(spidey2, tom_dir / "animations" / "climb_down")
    save_single_frame_anim(spidey3, tom_dir / "animations" / "wall_slide")
    save_single_frame_anim(spidey3, tom_dir / "animations" / "perch")
    save_single_frame_anim(spidey3, tom_dir / "animations" / "hang")
    save_single_frame_anim(spidey3, tom_dir / "animations" / "sleep")

    save_single_frame_anim(spidey2, tom_dir / "animations" / "swing")
    save_single_frame_anim(spidey1, tom_dir / "animations" / "interact")
    save_single_frame_anim(spidey2, tom_dir / "animations" / "dragged")

    print("Tom Holland poses and animation states integrated.")

if __name__ == "__main__":
    main()
