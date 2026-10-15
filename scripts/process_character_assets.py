"""Process raw generated images with pure Pillow: remove background, crop, generate idle and walk frames."""
import math
import os
import sys
import site
from pathlib import Path

# Ensure user site packages are available
user_site = site.getusersitepackages()
if os.path.exists(user_site) and user_site not in sys.path:
    sys.path.insert(0, user_site)
roaming_site = os.path.expanduser(r"~\AppData\Roaming\Python\Python313\site-packages")
if os.path.exists(roaming_site) and roaming_site not in sys.path:
    sys.path.insert(0, roaming_site)

from PIL import Image

def remove_background(image_path: Path) -> Image.Image:
    """Remove pure white/near-white background from image using pure Pillow."""
    img = Image.open(image_path).convert("RGBA")
    w, h = img.size
    
    datas = img.getdata()
    new_data = []
    
    for item in datas:
        r, g, b, a = item
        brightness = (r + g + b) / 3.0
        # If very close to white
        if brightness > 238 and abs(r - g) < 18 and abs(r - b) < 18:
            if brightness >= 250:
                new_data.append((r, g, b, 0))
            else:
                alpha = int(255 * (250 - brightness) / 12.0)
                new_data.append((r, g, b, alpha))
        else:
            new_data.append((r, g, b, 255))
            
    img.putdata(new_data)
    
    # Crop to non-transparent bounding box
    bbox = img.getbbox()
    if bbox:
        pad = 8
        crop_box = (
            max(0, bbox[0] - pad),
            max(0, bbox[1] - pad),
            min(w, bbox[2] + pad),
            min(h, bbox[3] + pad)
        )
        cropped = img.crop(crop_box)
    else:
        cropped = img

    # Resize to uniform 256x256 frame
    target_size = (256, 256)
    cropped.thumbnail((235, 235), Image.Resampling.LANCZOS)
    
    final_frame = Image.new("RGBA", target_size, (0, 0, 0, 0))
    paste_x = (target_size[0] - cropped.width) // 2
    paste_y = target_size[1] - cropped.height - 8
    final_frame.paste(cropped, (paste_x, paste_y), cropped)
    
    return final_frame

def generate_idle_frames(base_img: Image.Image, output_dir: Path, num_frames: int = 4):
    """Generate subtle breathing/bobbing idle animation frames."""
    output_dir.mkdir(parents=True, exist_ok=True)
    w, h = base_img.size
    
    for i in range(num_frames):
        frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        angle_rad = 2 * math.pi * i / num_frames
        offset_y = int(round(3 * math.sin(angle_rad)))
        
        scale_y = 1.0 + 0.02 * math.sin(angle_rad)
        scale_x = 1.0 - 0.01 * math.sin(angle_rad)
        
        new_w = int(round(w * scale_x))
        new_h = int(round(h * scale_y))
        
        scaled = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        paste_x = (w - new_w) // 2
        paste_y = (h - new_h) + offset_y
        
        frame.paste(scaled, (paste_x, paste_y), scaled)
        frame.save(output_dir / f"frame_{i}.png", "PNG")

def generate_walk_frames(base_img: Image.Image, output_dir: Path, num_frames: int = 6):
    """Generate walking animation frames with tilt, bobbing, and stride shift."""
    output_dir.mkdir(parents=True, exist_ok=True)
    w, h = base_img.size
    
    for i in range(num_frames):
        frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        phase = 2 * math.pi * i / num_frames
        
        bob_y = int(round(6 * abs(math.sin(phase))))
        angle = 4.0 * math.sin(phase)
        
        rotated = base_img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
        paste_x = int(round(3 * math.cos(phase)))
        paste_y = -bob_y
        
        frame.paste(rotated, (paste_x, paste_y), rotated)
        frame.save(output_dir / f"frame_{i}.png", "PNG")

def main():
    brain_dir = Path(r"C:\Users\Gaurav Patel\.gemini\antigravity-ide\brain\42ab382e-6f1a-4173-af3a-82553813f469")
    miles_src = brain_dir / "miles_chibi_1791972226138.jpg"
    tom_src = brain_dir / "tom_chibi_1791972329474.jpg"

    project_root = Path(__file__).resolve().parent.parent

    # Process Miles Morales
    if miles_src.exists():
        print(f"Processing Miles Morales from {miles_src}...")
        miles_base = remove_background(miles_src)
        miles_dir = project_root / "characters" / "miles_morales"
        
        (miles_dir / "sprites").mkdir(parents=True, exist_ok=True)
        miles_base.save(miles_dir / "sprites" / "idle.png", "PNG")
        miles_base.save(miles_dir / "preview.png", "PNG")
        
        generate_idle_frames(miles_base, miles_dir / "animations" / "idle")
        generate_walk_frames(miles_base, miles_dir / "animations" / "walk")
        print("Miles Morales processed successfully.")
    else:
        print(f"Error: Miles Morales source image not found at {miles_src}")

    # Process Tom Holland
    if tom_src.exists():
        print(f"Processing Tom Holland from {tom_src}...")
        tom_base = remove_background(tom_src)
        tom_dir = project_root / "characters" / "tom_holland"
        
        (tom_dir / "sprites").mkdir(parents=True, exist_ok=True)
        tom_base.save(tom_dir / "sprites" / "idle.png", "PNG")
        tom_base.save(tom_dir / "preview.png", "PNG")
        
        generate_idle_frames(tom_base, tom_dir / "animations" / "idle")
        generate_walk_frames(tom_base, tom_dir / "animations" / "walk")
        print("Tom Holland processed successfully.")
    else:
        print(f"Error: Tom Holland source image not found at {tom_src}")

if __name__ == "__main__":
    main()
