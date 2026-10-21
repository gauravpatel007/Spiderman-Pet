"""Clean and render all animation frames for spider_2 with transparent background."""
import json
import math
import sys
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PIL import Image
import numpy as np

from scripts.build_articulated_assets import pose


def clean_source_image(input_path: Path, output_path: Path) -> Image.Image:
    img = Image.open(input_path).convert('RGBA')
    arr = np.array(img)
    H, W = arr.shape[:2]

    # 1. Clean bottom shadow:
    for y in range(455, H):
        for x in range(W):
            in_left_boot = (188 <= x <= 228) and (y <= 483)
            in_right_boot = (290 <= x <= 326) and (y <= 489)
            if not (in_left_boot or in_right_boot):
                arr[y, x, 3] = 0
            else:
                px = arr[y, x, :3]
                if np.all(px > 190) or (np.all(px > 120) and np.std(px) < 8):
                    arr[y, x, 3] = 0

    # 2. Flood fill trapped white background from seeds
    seeds = [(200, 300), (295, 330), (256, 420)]
    visited = np.zeros((H, W), dtype=bool)

    for sx, sy in seeds:
        if visited[sy, sx]:
            continue
        queue = deque([(sx, sy)])
        visited[sy, sx] = True
        while queue:
            cx, cy = queue.popleft()
            arr[cy, cx, 3] = 0
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < W and 0 <= ny < H and not visited[ny, nx]:
                    px = arr[ny, nx]
                    if px[3] > 0 and (np.all(px[:3] > 190) or (np.all(px[:3] > 140) and np.std(px[:3]) < 10)):
                        visited[ny, nx] = True
                        queue.append((nx, ny))

    # 3. Clean edge halos and low alpha fringes below head (Y >= 240)
    for y in range(240, H):
        for x in range(W):
            if arr[y, x, 3] > 0:
                if arr[y, x, 3] < 30:
                    arr[y, x, 3] = 0
                elif np.all(arr[y, x, :3] > 180) and arr[y, x, 3] < 140:
                    arr[y, x, 3] = 0
                elif np.all(arr[y, x, :3] > 205):
                    arr[y, x, 3] = 0

    cleaned = Image.fromarray(arr)
    cleaned.save(output_path)
    return cleaned


def render_batch(task_list):
    clean_src_path = Path(__file__).resolve().parent / "cleaned_spider2_source.png"
    source = Image.open(clean_src_path)
    x0, y0, x1, y1 = source.getbbox()
    w, h = x1 - x0, y1 - y0
    head = round(y0 + h * .43)
    hip = round(y0 + h * .73)
    left, right, center = round(x0 + w * .28), round(x0 + w * .72), round((x0 + x1) / 2)
    rectangles = {
        'head': (x0, y0, x1, head),
        'torso': (left, head, right, hip),
        'arm_left': (x0, head, left, hip), 'arm_right': (right, head, x1, hip),
        'leg_left': (x0, hip, center, y1), 'leg_right': (center, hip, x1, y1),
    }
    parts, rig = {}, {'eyes': [], 'lid': '#202329'}
    for name, box in rectangles.items():
        layer = Image.new('RGBA', source.size)
        layer.paste(source.crop(box), box[:2])
        parts[name] = layer
        pivot = [center, head] if name == 'head' else [(box[0] + box[2]) / 2, box[1] + 4]
        rig[name] = {'pivot': pivot}

    for name, mapped_name, i, count, out_path_str in task_list:
        frame = pose(parts, rig, 2 * math.pi * i / count, mapped_name, i / max(1, count - 1))
        p = Path(out_path_str)
        p.parent.mkdir(parents=True, exist_ok=True)
        frame.save(p)
        if name == 'idle' and i == 0:
            frame.save(p.parents[2] / 'preview.png')
    return len(task_list)


def main():
    t0 = time.time()
    base_dir = Path(__file__).resolve().parent.parent
    root = base_dir / 'characters' / 'spider_2'
    
    clean_png = Path(__file__).resolve().parent / "cleaned_spider2_source.png"
    v2 = base_dir / "cleaned_spider2_idle_v2.png"
    if v2.exists():
        cleaned_img = Image.open(v2)
        cleaned_img.save(clean_png)
    else:
        idle_orig = root / 'sprites' / 'idle.png'
        cleaned_img = clean_source_image(idle_orig, clean_png)

    # Save to sprites/idle.png, preview.png, and Images/
    (root / 'sprites').mkdir(exist_ok=True)
    cleaned_img.save(root / 'sprites' / 'idle.png')
    cleaned_img.save(root / 'preview.png')
    cleaned_img.save(base_dir / 'Images' / 'spiderman 2 (transparent).png')

    template = json.loads((root / 'character.json').read_text(encoding='utf-8'))
    manifest = {'version': 1, 'canvas': [512, 512], 'anchor': [256, 488],
                'method': 'procedural imported cutout', 'animations': {}}
    specs = {'idle': (24,12,True), 'walk': (24,24,True), 'run': (16,24,True),
             'sleep': (24,8,True), 'wake_up': (18,12,False), 'sit': (24,12,True),
             'stand_up': (12,12,False), 'wave': (24,16,False), 'dance': (48,16,False),
             'celebrate': (32,16,False), 'dragged': (24,12,True)}
    other = {'jump': 'run', 'fall': 'dragged', 'land': 'sit', 'climb_up': 'walk',
             'climb_down': 'walk', 'wall_slide': 'dragged', 'perch': 'sit',
             'swing': 'dragged', 'hang': 'dragged', 'interact': 'wave'}

    all_tasks = []
    generated_clean = root / 'generated_clean'
    if generated_clean.exists():
        import shutil
        shutil.rmtree(generated_clean)
    generated_clean.mkdir(parents=True, exist_ok=True)

    for name in template['supported_animations']:
        count, fps, loop = specs.get(name, (12,12,name not in ('jump','land','interact')))
        frames = []
        for i in range(count):
            relative = f'generated/{name}/frame_{i:02d}.png'
            frames.append(relative)
            clean_out = generated_clean / name / f'frame_{i:02d}.png'
            all_tasks.append((name, other.get(name, name), i, count, str(clean_out)))
        manifest['animations'][name] = dict(frames=frames, fps=fps, loop=loop, mirror_allowed=True)

    n_workers = 8
    chunk_size = math.ceil(len(all_tasks) / n_workers)
    batches = [all_tasks[i:i + chunk_size] for i in range(0, len(all_tasks), chunk_size)]

    print(f'Starting render of {len(all_tasks)} frames in {len(batches)} batches across {n_workers} processes...')
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        results = list(pool.map(render_batch, batches))

    # Atomically swap generated_clean -> generated
    import shutil
    old_gen = root / 'generated'
    if old_gen.exists():
        shutil.rmtree(old_gen)
    generated_clean.rename(old_gen)

    (root / 'animation_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Rendered all {sum(results)} frames successfully in {time.time() - t0:.2f}s!')


if __name__ == '__main__':
    main()
