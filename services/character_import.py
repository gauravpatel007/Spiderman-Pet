"""Transactional local character imports with artwork-specific animation clips."""
import json
import math
import re
import shutil
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageOps
from scripts.build_articulated_assets import pose
from services.background_remover import auto_remove_background


def load_artwork(path, progress_callback=None):
    with Image.open(path) as opened:
        image = ImageOps.exif_transpose(opened).convert('RGBA')
    image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    
    # Automatically remove any solid, gradient, or complex background
    image = auto_remove_background(image, progress_callback=progress_callback)
    
    box = image.getchannel('A').getbbox()
    if not box:
        raise ValueError('Artwork is empty after background removal. Use a character image with a distinct background.')
    image = image.crop(box)
    image.thumbnail((400, 440), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (512, 512))
    canvas.alpha_composite(image, ((512-image.width)//2, 492-image.height))
    return canvas


def build_artwork_clips(root, artwork, template, progress_callback=None):
    """Use a conservative cutout rig; never substitute template character pixels."""
    source = load_artwork(artwork, progress_callback=progress_callback)
    (root/'sprites').mkdir(exist_ok=True)
    source.save(root/'sprites'/'idle.png', compress_level=1)
    x0, y0, x1, y1 = source.getbbox()
    w, h = x1-x0, y1-y0
    head = round(y0+h*.43)
    hip = round(y0+h*.73)
    left, right, center = round(x0+w*.28), round(x0+w*.72), round((x0+x1)/2)
    pad_y = max(8, round(h * 0.035))
    pad_x = max(6, round(w * 0.035))
    rectangles = {
        'head': (x0, y0, x1, min(y1, head + pad_y)),
        'torso': (max(x0, left - pad_x), max(y0, head - pad_y), min(x1, right + pad_x), min(y1, hip + pad_y)),
        'arm_left': (x0, max(y0, head - pad_y), min(x1, left + pad_x), hip),
        'arm_right': (max(x0, right - pad_x), max(y0, head - pad_y), x1, hip),
        'leg_left': (x0, max(y0, hip - pad_y), min(x1, center + pad_x), y1),
        'leg_right': (max(x0, center - pad_x), max(y0, hip - pad_y), x1, y1),
    }
    parts, rig = {}, {'eyes': [], 'lid': '#202329'}
    for name, box in rectangles.items():
        layer = Image.new('RGBA', source.size)
        layer.paste(source.crop(box), box[:2])
        parts[name] = layer
        pivot = [center, head] if name == 'head' else [(box[0]+box[2])/2, box[1]+4]
        rig[name] = {'pivot': pivot}
    manifest = {'version': 1, 'canvas': [512, 512], 'anchor': [256, 488],
                'method': 'procedural imported cutout', 'animations': {}}
    specs = {'idle': (24,12,True), 'walk': (24,24,True), 'run': (16,24,True),
             'sleep': (24,8,True), 'wake_up': (18,12,False), 'sit': (24,12,True),
             'stand_up': (12,12,False), 'wave': (24,16,False), 'dance': (48,16,False),
             'celebrate': (32,16,False), 'dragged': (24,12,True)}
    other = {'jump': 'run', 'fall': 'dragged', 'land': 'sit', 'climb_up': 'walk',
             'climb_down': 'walk', 'wall_slide': 'dragged', 'perch': 'sit',
             'swing': 'dragged', 'hang': 'dragged', 'interact': 'wave'}
    
    animations = template.get('supported_animations', list(specs.keys()))
    total = len(animations)
    for idx, name in enumerate(animations):
        if progress_callback:
            pct = 15 + int((idx / max(1, total)) * 75)
            progress_callback(pct, f"Generating '{name}' ({idx + 1}/{total})...")
        count, fps, loop = specs.get(name, (12,12,name not in ('jump','land','interact')))
        folder = root/'generated'/name
        folder.mkdir(parents=True, exist_ok=True)
        frames = []
        for i in range(count):
            frame = pose(parts, rig, 2*math.pi*i/count, other.get(name,name), i/max(1,count-1))
            relative = f'generated/{name}/frame_{i:02d}.png'
            frame.save(root/relative, compress_level=1)
            frames.append(relative)
            if name == 'idle' and i == 0:
                frame.save(root/'preview.png', compress_level=1)
        manifest['animations'][name] = dict(frames=frames, fps=fps, loop=loop, mirror_allowed=True)
    
    if progress_callback:
        progress_callback(92, 'Writing animation manifest...')
    (root/'animation_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return list(manifest['animations'])


def create_character(destination_root, template_root, cid, name, suit, artwork=None, progress_callback=None):
    if not re.fullmatch(r'[a-z0-9_]+', cid) or cid in ('con','prn','aux','nul') or re.fullmatch(r'(com|lpt)[0-9]', cid):
        raise ValueError('Choose a valid character identifier (letters, numbers and underscores).')
    destination_root, template_root = Path(destination_root), Path(template_root)
    target = destination_root/cid
    if target.exists():
        raise ValueError('This character identifier already exists. Choose another.')
    
    # Clean up any leftover temporary staging folders from previous interrupted runs
    if destination_root.exists():
        for old_stage in destination_root.glob('.import-*'):
            shutil.rmtree(old_stage, ignore_errors=True)

    template = json.loads((template_root/'character.json').read_text(encoding='utf-8'))
    destination_root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.import-', dir=destination_root))
    try:
        if artwork:
            if progress_callback:
                progress_callback(5, 'Detecting and removing background...')
            supported = build_artwork_clips(stage, artwork, template, progress_callback=progress_callback)
        else:
            if progress_callback:
                progress_callback(30, 'Cloning template character...')
            for child in template_root.iterdir():
                if child.is_dir():
                    shutil.copytree(child, stage/child.name)
                elif child.name != 'character.json':
                    shutil.copy2(child, stage/child.name)
            supported = template['supported_animations']
        
        if progress_callback:
            progress_callback(95, 'Writing character profile...')
        data = dict(template, id=cid, name=name, display_name=name, suit=suit,
                    personality=template.get('personality', template['id']),
                    supported_animations=supported, custom_character=True,
                    animation_source='imported_artwork' if artwork else 'template_copy')
        (stage/'character.json').write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        
        # Resilient move/rename for Windows file locking
        renamed = False
        for _ in range(5):
            try:
                stage.rename(target)
                renamed = True
                break
            except (PermissionError, OSError):
                time.sleep(0.08)
        if not renamed:
            shutil.move(str(stage), str(target))
        
        if progress_callback:
            progress_callback(100, 'Done!')
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)
    return target
